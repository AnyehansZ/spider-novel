"""
NovelForge AI Enhancer
Uses Google Gemini API to improve machine-translated novel text.
Features: retry logic, rate limiting, batch processing, progress tracking.
"""

import os
import csv
import time
import logging
from pathlib import Path
from typing import Optional, List
import json

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

from error_handler import (
    retry_with_backoff,
    EnhancerError,
    APIKeyError,
    APIConnectionError,
    APIRateLimitError,
    APIResponseError,
    ErrorSummary,
    ErrorContext,
)
from manifest_manager import ManifestManager
import utils
import config as cfg
import validators

logger = logging.getLogger("NovelForge.Enhancer")


# ============================================================================
# ENHANCEMENT API WRAPPER
# ============================================================================

class EnhanceAPI:
    """
    Wrapper around Google Gemini API for text enhancement.
    Handles authentication, rate limiting, retries, and error recovery.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the API wrapper.
        
        Args:
            api_key: Google Gemini API key (defaults to environment variable)
        
        Raises:
            APIKeyError: If no API key provided or invalid
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise APIKeyError(
                "No Google Gemini API key found. "
                "Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )
        
        # Validate API key format
        try:
            validators.validate_api_key(self.api_key, "Google Gemini")
        except validators.ValidationError as e:
            raise APIKeyError(str(e))
        
        # Configure Gemini SDK
        self.client = None
        self._initialize_client()
        
        self.model = cfg.DEFAULT_AI_MODEL
        self.temperature = cfg.GEMINI_TEMPERATURE
        self.max_tokens = cfg.GEMINI_MAX_TOKENS
        self.timeout = cfg.GEMINI_API_TIMEOUT
        
        logger.info(f"Initialized EnhanceAPI with model: {self.model}")
    
    def _initialize_client(self):
        """Initialize Gemini client."""
        if not genai:
            raise APIConnectionError(
                "google-genai library not installed. "
                "Run: pip install google-genai"
            )
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.Client()
            logger.debug("Gemini client initialized successfully")
        except Exception as e:
            raise APIConnectionError(f"Failed to initialize Gemini client: {str(e)}")
    
    def set_model(self, model: str):
        """Change the AI model."""
        if model not in cfg.AVAILABLE_AI_MODELS:
            raise ValueError(f"Unknown model: {model}")
        self.model = model
        logger.info(f"Switched to model: {model}")
    
    @retry_with_backoff(
        max_attempts=cfg.GEMINI_MAX_RETRIES,
        base_delay=cfg.GEMINI_RETRY_DELAY,
        exceptions=(APIRateLimitError, APIConnectionError),
    )
    def process_text(self, text: str) -> str:
        """
        Enhance text using Gemini API.
        Automatically retries on rate limit or transient errors.
        
        Args:
            text: Raw machine-translated text to enhance
        
        Returns:
            Enhanced text
        
        Raises:
            APIResponseError: If API returns error
            APIRateLimitError: If rate limit exceeded (will retry)
            APIConnectionError: If connection fails
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
        
        try:
            logger.debug(f"Sending {len(text)} chars to {self.model}")
            
            # Build the prompt
            prompt = cfg.ENHANCEMENT_PROMPT_TEMPLATE.format(body=text)
            
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    top_p=0.9,
                    top_k=40,
                ),
            )
            
            # Handle response
            if not response or not response.text:
                raise APIResponseError("Received empty response from API")
            
            enhanced = response.text.strip()
            logger.debug(f"Received {len(enhanced)} chars back from API")
            return enhanced
        
        except genai.APIError as e:
            # Check if rate limit error
            if "429" in str(e) or "rate limit" in str(e).lower():
                logger.warning(f"Rate limit hit: {str(e)}")
                raise APIRateLimitError(str(e))
            
            logger.error(f"API error: {str(e)}")
            raise APIResponseError(f"API error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error in process_text: {str(e)}")
            raise APIConnectionError(f"Unexpected error: {str(e)}")
    
    def batch_process(
        self,
        texts: List[str],
        delay: float = cfg.ENHANCEMENT_BATCH_DELAY,
    ) -> List[str]:
        """
        Process multiple texts with rate limiting between requests.
        
        Args:
            texts: List of texts to enhance
            delay: Delay in seconds between API calls
        
        Returns:
            List of enhanced texts (same length as input)
        """
        results = []
        
        for i, text in enumerate(texts):
            try:
                enhanced = self.process_text(text)
                results.append(enhanced)
                
                # Rate limiting
                if i < len(texts) - 1:
                    time.sleep(delay)
            
            except Exception as e:
                logger.error(f"Failed to enhance text {i}: {str(e)}")
                results.append(text)  # Return original on error
        
        return results
    
    def health_check(self) -> bool:
        """
        Check if API connection is working.
        
        Returns:
            True if API is accessible
        """
        try:
            response = self.client.models.list()
            logger.info("API health check passed")
            return True
        except Exception as e:
            logger.error(f"API health check failed: {str(e)}")
            return False


# ============================================================================
# BATCH ENHANCER
# ============================================================================

class BatchEnhancer:
    """
    Enhance all chapters in a folder using the Gemini API.
    Tracks progress, handles errors, skips already-enhanced chapters.
    """
    
    def __init__(self, api: EnhanceAPI, novel_slug: str = None):
        """
        Initialize batch enhancer.
        
        Args:
            api: EnhanceAPI instance
            novel_slug: Optional slug for manifest tracking
        """
        self.api = api
        self.manifest_manager = ManifestManager()
        self.novel_slug = novel_slug
        self.error_summary = ErrorSummary("Enhancement")
        self.manifest = None
        
        if novel_slug:
            self.manifest = manifest_manager.load_manifest(novel_slug)
    
    def enhance_folder(
        self,
        folder_path: Path,
        skip_enhanced: bool = cfg.SKIP_ALREADY_ENHANCED,
    ) -> bool:
        """
        Enhance all chapters in a folder.
        
        Args:
            folder_path: Path to folder with chapter CSVs
            skip_enhanced: If True, skip chapters marked as enhanced
        
        Returns:
            True if all chapters enhanced successfully
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            logger.error(f"Folder not found: {folder_path}")
            return False
        
        # Get list of chapter files
        files = sorted([
            f for f in folder_path.iterdir()
            if f.name.startswith('chapter_') and f.suffix == '.csv'
        ], key=lambda f: utils.extract_chapter_number_from_filename(f.name))
        
        if not files:
            logger.warning(f"No chapter CSV files found in {folder_path}")
            return True
        
        logger.info(f"Found {len(files)} chapters to process")
        
        # Health check before starting
        if not self.api.health_check():
            logger.error("API health check failed. Cannot proceed.")
            return False
        
        # Process chapters
        for i, filepath in enumerate(files):
            chapter_num = utils.extract_chapter_number_from_filename(filepath.name)
            
            try:
                # Load chapter data
                result = utils.load_chapter_from_csv(filepath, logger)
                if not result:
                    logger.warning(f"Skipping chapter {chapter_num}: could not load")
                    self.error_summary.add_warning(chapter_num, "Could not load CSV")
                    continue
                
                title, editor, body, enhanced = result
                
                # Skip if already enhanced
                if skip_enhanced and enhanced.lower() == 'true':
                    logger.debug(f"Skipping chapter {chapter_num}: already enhanced")
                    self.error_summary.record_success()
                    continue
                
                # Enhance the text
                logger.info(f"Enhancing chapter {chapter_num}: {title}")
                enhanced_body = self.api.process_text(body)
                
                # Save enhanced version
                success = utils.update_chapter_csv(
                    filepath,
                    body_text=enhanced_body,
                    enhanced="True",
                    logger_obj=logger,
                )
                
                if success:
                    self.error_summary.record_success()
                    
                    # Update manifest
                    if self.manifest:
                        self.manifest.mark_enhanced(chapter_num)
                        self.manifest_manager.save_manifest(
                            self.manifest, self.novel_slug
                        )
                else:
                    self.error_summary.add_error(
                        chapter_num,
                        Exception("Failed to update CSV"),
                    )
            
            except Exception as e:
                logger.error(f"Failed to enhance chapter {chapter_num}: {str(e)}")
                self.error_summary.add_error(chapter_num, e)
                
                # Update manifest
                if self.manifest:
                    self.manifest.mark_error(chapter_num, str(e))
        
        # Report results
        logger.info(self.error_summary.get_report())
        
        return len(self.error_summary.errors) == 0


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

def enhance_folder(
    folder_path: Path,
    api_key: str = None,
    model: str = cfg.DEFAULT_AI_MODEL,
    skip_enhanced: bool = cfg.SKIP_ALREADY_ENHANCED,
) -> bool:
    """
    Convenience function to enhance all chapters in a folder.
    
    Args:
        folder_path: Path to folder with chapter CSVs
        api_key: Google Gemini API key
        model: Model to use
        skip_enhanced: Skip already-enhanced chapters
    
    Returns:
        True if successful
    """
    try:
        # Initialize API
        api = EnhanceAPI(api_key)
        api.set_model(model)
        
        # Run batch enhancement
        enhancer = BatchEnhancer(api)
        return enhancer.enhance_folder(folder_path, skip_enhanced)
    
    except Exception as e:
        logger.error(f"Enhancement failed: {str(e)}")
        return False


def health_check(api_key: str = None) -> bool:
    """
    Check if API key is valid and API is accessible.
    
    Args:
        api_key: Google Gemini API key
    
    Returns:
        True if API is healthy
    """
    try:
        api = EnhanceAPI(api_key)
        return api.health_check()
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False