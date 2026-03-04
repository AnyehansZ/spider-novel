"""
NovelForge Utilities Module
Centralized logging, CSV operations, and helper functions.
All file operations use Windows-safe path handling.
"""

import os
import csv
import re
import logging
import io
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import List, Tuple, Optional

import config as cfg
from error_handler import SafeFileOperation, ValidationError

# ============================================================================
# LOGGING SETUP (Global)
# ============================================================================

def setup_logging(
    log_level: str = cfg.LOG_LEVEL,
    log_file: Path = None,
) -> logging.Logger:
    """
    Initialize the logging system for the entire application.
    Configures both file and console logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (defaults to config)
    
    Returns:
        Root logger instance
    """
    log_file = Path(log_file or cfg.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create root logger
    root_logger = logging.getLogger("NovelForge")
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to prevent duplicates
    root_logger.handlers = []
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=cfg.LOG_MAX_BYTES,
        backupCount=cfg.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(cfg.LOG_FORMAT, cfg.LOG_DATE_FORMAT))
    file_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(cfg.LOG_FORMAT, cfg.LOG_DATE_FORMAT))
    console_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    root_logger.info(f"Logging initialized at {log_file}")
    return root_logger


# Get module logger
logger = logging.getLogger("NovelForge.Utils")


# ============================================================================
# FILE & DIRECTORY OPERATIONS
# ============================================================================

def ensure_folder(folder_path: Path, logger_obj: logging.Logger = None) -> Path:
    """
    Create a folder if it doesn't exist.
    Windows-safe path handling.
    
    Args:
        folder_path: Path to folder
        logger_obj: Optional logger instance
    
    Returns:
        Path object
    """
    logger_obj = logger_obj or logger
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            logger_obj.info(f"Created folder: {folder_path}")
        except Exception as e:
            logger_obj.error(f"Failed to create folder {folder_path}: {str(e)}")
            raise
    
    return folder_path


def safe_delete_file(file_path: Path, logger_obj: logging.Logger = None) -> bool:
    """
    Safely delete a file with error handling.
    
    Args:
        file_path: Path to file
        logger_obj: Optional logger instance
    
    Returns:
        True if deleted, False if not found or error
    """
    logger_obj = logger_obj or logger
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    try:
        file_path.unlink()
        logger_obj.info(f"Deleted file: {file_path}")
        return True
    except Exception as e:
        logger_obj.error(f"Failed to delete {file_path}: {str(e)}")
        return False


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    file_path = Path(file_path)
    if file_path.exists():
        return file_path.stat().st_size / (1024 * 1024)
    return 0


# ============================================================================
# CHAPTER NUMBER UTILITIES
# ============================================================================

def extract_chapter_number_from_filename(filename: str) -> int:
    """
    Extract chapter number from standard filename (chapter_XXXX.csv).
    
    Args:
        filename: Filename like 'chapter_0001.csv'
    
    Returns:
        Chapter number as integer, or 0 if not found
    """
    match = re.search(r'chapter_(\d+)', filename)
    if match:
        return int(match.group(1))
    return 0


def get_downloaded_chapters(folder_path: Path, logger_obj: logging.Logger = None) -> List[int]:
    """
    Get list of chapter numbers that have been downloaded.
    Scans the folder for chapter_*.csv files.
    
    Args:
        folder_path: Path to folder with chapter CSVs
        logger_obj: Optional logger instance
    
    Returns:
        Sorted list of chapter numbers
    """
    logger_obj = logger_obj or logger
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        logger_obj.debug(f"Folder not found: {folder_path}")
        return []
    
    try:
        files = [
            f for f in folder_path.iterdir()
            if f.is_file() and f.name.startswith('chapter_') and f.suffix == '.csv'
        ]
        
        chapter_nums = [extract_chapter_number_from_filename(f.name) for f in files]
        return sorted(set(chapter_nums))
    
    except Exception as e:
        logger_obj.error(f"Failed to scan folder {folder_path}: {str(e)}")
        return []


def get_missing_chapters(folder_path: Path, max_chapter: int) -> List[int]:
    """
    Identify missing chapters in a sequence.
    
    Args:
        folder_path: Path to folder with chapter CSVs
        max_chapter: Expected maximum chapter number
    
    Returns:
        List of missing chapter numbers
    """
    downloaded = get_downloaded_chapters(folder_path)
    if not downloaded:
        return list(range(1, max_chapter + 1))
    
    all_chapters = set(range(1, max(downloaded[-1], max_chapter) + 1))
    downloaded_set = set(downloaded)
    return sorted(all_chapters - downloaded_set)


# ============================================================================
# CSV OPERATIONS
# ============================================================================

def save_chapter_to_csv(
    folder_path: Path,
    chapter_num: int,
    title: str,
    edited_by: str,
    body_text: str,
    enhanced: str = "False",
    logger_obj: logging.Logger = None,
) -> bool:
    """
    Save a chapter to a CSV file with proper validation and encoding.
    Uses Windows-safe path handling.
    
    Args:
        folder_path: Path to folder
        chapter_num: Chapter number
        title: Chapter title
        edited_by: Editor name
        body_text: Chapter body content
        enhanced: "True" or "False" indicating if AI-enhanced
        logger_obj: Optional logger instance
    
    Returns:
        True if successful, False otherwise
    """
    logger_obj = logger_obj or logger
    
    try:
        # Validate data
        from validators import validate_chapter_data
        chapter_num, title, edited_by, body_text = validate_chapter_data(
            chapter_num, title, edited_by, body_text
        )
        
        # Ensure folder exists
        folder_path = ensure_folder(folder_path, logger_obj)
        
        # Build filename (Windows-safe)
        filename = f"chapter_{chapter_num:04d}.csv"
        filepath = folder_path / filename
        
        # Use safe file operation context manager
        with SafeFileOperation(filepath, 'w', 'utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            writer.writerow(["Title", "Edited By", "Chapter Body", "Enhanced"])
            writer.writerow([title, edited_by, body_text, enhanced])
        
        logger_obj.info(f"Saved chapter {chapter_num}: {title} to {filepath}")
        return True
    
    except ValidationError as e:
        logger_obj.error(f"Validation error saving chapter {chapter_num}: {str(e)}")
        return False
    except Exception as e:
        logger_obj.error(f"Failed to save chapter {chapter_num}: {str(e)}")
        return False


def load_chapter_from_csv(
    file_path: Path,
    logger_obj: logging.Logger = None,
) -> Optional[Tuple[str, str, str, str]]:
    """
    Load a chapter from a CSV file.
    
    Args:
        file_path: Path to chapter CSV file
        logger_obj: Optional logger instance
    
    Returns:
        Tuple of (title, edited_by, body, enhanced) or None if error
    """
    logger_obj = logger_obj or logger
    file_path = Path(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            
            if not headers or len(headers) < 4:
                logger_obj.error(f"Invalid CSV format in {file_path}")
                return None
            
            row = next(reader, None)
            if not row or len(row) < 4:
                logger_obj.warning(f"Empty chapter in {file_path}")
                return None
            
            return tuple(row[:4])
    
    except Exception as e:
        logger_obj.error(f"Failed to load {file_path}: {str(e)}")
        return None


def update_chapter_csv(
    file_path: Path,
    title: str = None,
    edited_by: str = None,
    body_text: str = None,
    enhanced: str = None,
    logger_obj: logging.Logger = None,
) -> bool:
    """
    Update specific fields in a chapter CSV (e.g., enhancement status).
    
    Args:
        file_path: Path to chapter CSV file
        title: New title (None to keep existing)
        edited_by: New editor (None to keep existing)
        body_text: New body (None to keep existing)
        enhanced: New enhanced status (None to keep existing)
        logger_obj: Optional logger instance
    
    Returns:
        True if successful, False otherwise
    """
    logger_obj = logger_obj or logger
    file_path = Path(file_path)
    
    try:
        # Load current data
        current = load_chapter_from_csv(file_path, logger_obj)
        if not current:
            return False
        
        # Merge with new data
        current_title, current_editor, current_body, current_enhanced = current
        
        new_title = title if title is not None else current_title
        new_editor = edited_by if edited_by is not None else current_editor
        new_body = body_text if body_text is not None else current_body
        new_enhanced = enhanced if enhanced is not None else current_enhanced
        
        # Validate
        from validators import validate_chapter_data
        chapter_num = extract_chapter_number_from_filename(file_path.name)
        validate_chapter_data(chapter_num, new_title, new_editor, new_body)
        
        # Save
        with SafeFileOperation(file_path, 'w', 'utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            writer.writerow(["Title", "Edited By", "Chapter Body", "Enhanced"])
            writer.writerow([new_title, new_editor, new_body, new_enhanced])
        
        logger_obj.info(f"Updated chapter {chapter_num}")
        return True
    
    except Exception as e:
        logger_obj.error(f"Failed to update {file_path}: {str(e)}")
        return False


# ============================================================================
# STRING UTILITIES
# ============================================================================

def clean_text(text: str) -> str:
    """
    Clean text: remove extra whitespace, normalize line endings.
    
    Args:
        text: Text to clean
    
    Returns:
        Cleaned text
    """
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove multiple consecutive newlines
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to max length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add (e.g., "...")
    
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


# ============================================================================
# PROGRESS UTILITIES
# ============================================================================

class SimpleProgress:
    """Simple progress tracker without external dependencies."""
    
    def __init__(self, total: int, prefix: str = ""):
        self.total = total
        self.current = 0
        self.prefix = prefix
    
    def update(self, amount: int = 1, message: str = ""):
        """Update progress."""
        self.current = min(self.current + amount, self.total)
        if message:
            logger.info(f"{self.prefix} {message} ({self.current}/{self.total})")
    
    def get_percent(self) -> int:
        """Get progress as percentage."""
        if self.total == 0:
            return 0
        return int((self.current / self.total) * 100)


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

# For backwards compatibility with old code
logger_instance = logging.getLogger("NovelForge")