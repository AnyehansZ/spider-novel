"""
NovelForge Settings Manager
Persistent configuration storage for API keys, preferences, and application state.
"""

import json
import os
import logging
from pathlib import Path
from typing import Any, Optional, Dict

from error_handler import ConfigurationError

logger = logging.getLogger("NovelForge.SettingsManager")


class SettingsManager:
    """
    Manage application settings with persistent JSON storage.
    Supports API key encryption, model selection, and cleanup preferences.
    """
    
    # Default settings
    DEFAULT_SETTINGS = {
        "GOOGLE_API_KEY": "",
        "CLEANUP_MODE": "Ask",  # Ask, Always, Never
        "AI_MODEL": "gemini-2.5-flash",
        "CRAWLER_DELAY_MIN": 1.0,
        "CRAWLER_DELAY_MAX": 3.0,
        "ENABLE_LOGGING": True,
        "LOG_LEVEL": "INFO",
    }
    
    CLEANUP_MODES = {
        "Always": "Delete raw CSVs after EPUB compilation",
        "Ask": "Prompt me each time",
        "Never": "Keep all CSV files",
    }
    
    AVAILABLE_MODELS = {
        "gemini-3.0-flash": "Flash 3.0 (Newest, Fastest)",
        "gemini-2.5-flash": "Flash 2.5 (Stable, Recommended)",
        "gemini-2.0-flash": "Flash 2.0 (Legacy)",
    }
    
    def __init__(self, config_file: Path = None):
        """
        Initialize settings manager.
        
        Args:
            config_file: Path to config JSON file
                        (defaults to ~/NovelForge/config/settings.json)
        """
        if config_file is None:
            # Default path
            config_dir = Path.home() / "NovelForge" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "settings.json"
        
        self.config_file = Path(config_file)
        self.settings: Dict[str, Any] = self.load_settings()
        
        logger.info(f"Settings loaded from {self.config_file}")
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from file.
        Returns defaults if file doesn't exist.
        
        Returns:
            Settings dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Merge with defaults (in case new keys were added)
                merged = self.DEFAULT_SETTINGS.copy()
                merged.update(data)
                
                logger.debug(f"Loaded settings from {self.config_file}")
                return merged
            
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load settings: {str(e)}, using defaults")
                return self.DEFAULT_SETTINGS.copy()
        
        logger.debug(f"Settings file not found: {self.config_file}")
        return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self) -> bool:
        """
        Save settings to file.
        
        Returns:
            True if successful
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Settings saved to {self.config_file}")
            return True
        
        except IOError as e:
            logger.error(f"Failed to save settings: {str(e)}")
            return False
    
    # ====================================================================
    # GETTERS & SETTERS
    # ====================================================================
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if key not found
        
        Returns:
            Setting value
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set a setting value and save to disk.
        
        Args:
            key: Setting key
            value: Setting value
        
        Returns:
            True if successful
        """
        self.settings[key] = value
        logger.debug(f"Setting {key} = {value}")
        return self.save_settings()
    
    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults."""
        self.settings = self.DEFAULT_SETTINGS.copy()
        logger.info("Reset settings to defaults")
        return self.save_settings()
    
    # ====================================================================
    # API KEY MANAGEMENT
    # ====================================================================
    
    def get_api_key(self) -> Optional[str]:
        """Get stored API key (or from environment)."""
        # Check stored setting first
        stored = self.get("GOOGLE_API_KEY")
        if stored:
            return stored
        
        # Fall back to environment variable
        return os.environ.get("GOOGLE_API_KEY")
    
    def set_api_key(self, api_key: str) -> bool:
        """
        Store API key.
        
        Args:
            api_key: Google Gemini API key
        
        Returns:
            True if successful
        """
        if not api_key or not isinstance(api_key, str):
            logger.error("Invalid API key format")
            return False
        
        # Also set environment variable for current session
        os.environ["GOOGLE_API_KEY"] = api_key.strip()
        
        return self.set("GOOGLE_API_KEY", api_key.strip())
    
    def has_api_key(self) -> bool:
        """Check if API key is configured."""
        return bool(self.get_api_key())
    
    # ====================================================================
    # MODEL MANAGEMENT
    # ====================================================================
    
    def get_model(self) -> str:
        """Get selected AI model."""
        model = self.get("AI_MODEL")
        if model not in self.AVAILABLE_MODELS:
            logger.warning(f"Unknown model {model}, using default")
            return list(self.AVAILABLE_MODELS.keys())[0]
        return model
    
    def set_model(self, model: str) -> bool:
        """
        Set AI model.
        
        Args:
            model: Model identifier
        
        Returns:
            True if valid model
        """
        if model not in self.AVAILABLE_MODELS:
            logger.error(f"Unknown model: {model}")
            return False
        
        return self.set("AI_MODEL", model)
    
    # ====================================================================
    # CLEANUP MODE MANAGEMENT
    # ====================================================================
    
    def get_cleanup_mode(self) -> str:
        """Get cleanup mode (Ask, Always, Never)."""
        mode = self.get("CLEANUP_MODE")
        if mode not in self.CLEANUP_MODES:
            logger.warning(f"Unknown cleanup mode {mode}, using Ask")
            return "Ask"
        return mode
    
    def set_cleanup_mode(self, mode: str) -> bool:
        """
        Set cleanup mode.
        
        Args:
            mode: One of: Ask, Always, Never
        
        Returns:
            True if valid mode
        """
        if mode not in self.CLEANUP_MODES:
            logger.error(f"Unknown cleanup mode: {mode}")
            return False
        
        return self.set("CLEANUP_MODE", mode)
    
    # ====================================================================
    # CRAWLER SETTINGS
    # ====================================================================
    
    def get_crawler_delays(self) -> tuple:
        """Get crawler delay range (min, max)."""
        min_delay = self.get("CRAWLER_DELAY_MIN", 1.0)
        max_delay = self.get("CRAWLER_DELAY_MAX", 3.0)
        return float(min_delay), float(max_delay)
    
    def set_crawler_delays(self, min_delay: float, max_delay: float) -> bool:
        """
        Set crawler delay range.
        
        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
        
        Returns:
            True if valid
        """
        if min_delay < 0 or max_delay < min_delay:
            logger.error("Invalid delay range")
            return False
        
        self.set("CRAWLER_DELAY_MIN", min_delay)
        return self.set("CRAWLER_DELAY_MAX", max_delay)
    
    # ====================================================================
    # LOGGING SETTINGS
    # ====================================================================
    
    def get_log_level(self) -> str:
        """Get logging level."""
        level = self.get("LOG_LEVEL", "INFO")
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if level not in valid_levels:
            logger.warning(f"Unknown log level {level}")
            return "INFO"
        return level
    
    def set_log_level(self, level: str) -> bool:
        """
        Set logging level.
        
        Args:
            level: One of: DEBUG, INFO, WARNING, ERROR, CRITICAL
        
        Returns:
            True if valid
        """
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if level.upper() not in valid_levels:
            logger.error(f"Unknown log level: {level}")
            return False
        
        return self.set("LOG_LEVEL", level.upper())
    
    # ====================================================================
    # IMPORT/EXPORT
    # ====================================================================
    
    def export_settings(self, output_path: Path) -> bool:
        """
        Export settings to file.
        Note: API key is included!
        
        Args:
            output_path: Path to export file
        
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.info(f"Settings exported to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export settings: {str(e)}")
            return False
    
    def import_settings(self, input_path: Path) -> bool:
        """
        Import settings from file.
        
        Args:
            input_path: Path to import file
        
        Returns:
            True if successful
        """
        try:
            input_path = Path(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            
            self.settings.update(imported)
            self.save_settings()
            
            logger.info(f"Settings imported from {input_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to import settings: {str(e)}")
            return False
    
    # ====================================================================
    # VALIDATION
    # ====================================================================
    
    def validate(self) -> bool:
        """
        Validate all settings.
        
        Returns:
            True if all settings are valid
        """
        errors = []
        
        # Validate API key format if present
        if self.get("GOOGLE_API_KEY"):
            if len(self.get("GOOGLE_API_KEY")) < 10:
                errors.append("API key too short")
        
        # Validate model
        if self.get("AI_MODEL") not in self.AVAILABLE_MODELS:
            errors.append(f"Unknown model: {self.get('AI_MODEL')}")
        
        # Validate cleanup mode
        if self.get("CLEANUP_MODE") not in self.CLEANUP_MODES:
            errors.append(f"Unknown cleanup mode: {self.get('CLEANUP_MODE')}")
        
        # Validate log level
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.get("LOG_LEVEL") not in valid_levels:
            errors.append(f"Unknown log level: {self.get('LOG_LEVEL')}")
        
        if errors:
            for error in errors:
                logger.error(f"Settings validation error: {error}")
            return False
        
        logger.debug("Settings validation passed")
        return True