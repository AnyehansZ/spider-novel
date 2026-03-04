"""
NovelForge Input Validation & Sanitization
Protects against path traversal, CSV injection, and invalid data.
"""

import re
import csv
import io
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse
import logging

from error_handler import ValidationError
import config as cfg

logger = logging.getLogger("NovelForge.Validators")


# ============================================================================
# PATH VALIDATION & SANITIZATION
# ============================================================================

def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize a filename to prevent directory traversal attacks.
    
    Args:
        filename: Raw filename input
        max_length: Maximum filename length
    
    Returns:
        Safe filename
    
    Raises:
        ValidationError: If filename is invalid or dangerous
    """
    if not filename or not isinstance(filename, str):
        raise ValidationError("Filename must be a non-empty string")
    
    # Remove path separators and traversal attempts
    filename = filename.replace('\\', '_').replace('/', '_')
    filename = filename.replace('..', '_')
    filename = filename.replace(':', '_')
    
    # Remove Windows forbidden characters
    forbidden = r'<>:"|?*'
    for char in forbidden:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots (Windows reserved)
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip()
    
    if not filename:
        raise ValidationError("Filename cannot be empty after sanitization")
    
    logger.debug(f"Sanitized filename: '{filename}'")
    return filename


def validate_output_path(base_path: Path, relative_path: str) -> Path:
    """
    Validate that a relative path doesn't escape the base directory.
    Prevents path traversal attacks like ../../etc/passwd
    
    Args:
        base_path: Base directory (e.g., novels/)
        relative_path: User-provided relative path (e.g., my-novel/)
    
    Returns:
        Resolved Path object within base_path
    
    Raises:
        ValidationError: If path tries to escape base directory
    """
    base_path = Path(base_path).resolve()
    
    # Sanitize the relative path
    relative_path = relative_path.replace('\\', '/').replace('..', '_')
    
    # Construct and resolve the full path
    full_path = (base_path / relative_path).resolve()
    
    # Verify the resolved path is still within base_path
    try:
        full_path.relative_to(base_path)
    except ValueError:
        raise ValidationError(
            f"Path traversal detected: {relative_path} attempts to escape {base_path}"
        )
    
    logger.debug(f"Validated path: {full_path}")
    return full_path


def ensure_safe_directory(dir_path: Path, create: bool = True) -> Path:
    """
    Ensure a directory path is safe and exists.
    
    Args:
        dir_path: Directory path to validate
        create: If True, create the directory if it doesn't exist
    
    Returns:
        Resolved Path object
    
    Raises:
        ValidationError: If path is unsafe
    """
    dir_path = Path(dir_path).resolve()
    
    # Check path length (Windows limit is 260)
    if len(str(dir_path)) > cfg.MAX_PATH_LENGTH:
        raise ValidationError(f"Path too long (max {cfg.MAX_PATH_LENGTH}): {dir_path}")
    
    if create:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ValidationError(f"Cannot create directory {dir_path}: {str(e)}")
    else:
        if not dir_path.is_dir():
            raise ValidationError(f"Directory does not exist: {dir_path}")
    
    return dir_path


# ============================================================================
# DATA VALIDATION
# ============================================================================

def validate_chapter_data(
    chapter_num: int,
    title: str,
    edited_by: str,
    body: str,
) -> Tuple[int, str, str, str]:
    """
    Validate chapter data before saving.
    
    Args:
        chapter_num: Chapter number
        title: Chapter title
        edited_by: Editor name
        body: Chapter body text
    
    Returns:
        Tuple of validated (chapter_num, title, edited_by, body)
    
    Raises:
        ValidationError: If any field is invalid
    """
    # Validate chapter number
    if not isinstance(chapter_num, int):
        raise ValidationError(f"Chapter number must be integer, got {type(chapter_num)}")
    
    if not (cfg.MIN_CHAPTER_NUMBER <= chapter_num <= cfg.MAX_CHAPTER_NUMBER):
        raise ValidationError(
            f"Chapter number {chapter_num} out of range "
            f"({cfg.MIN_CHAPTER_NUMBER}-{cfg.MAX_CHAPTER_NUMBER})"
        )
    
    # Validate title
    if not isinstance(title, str):
        raise ValidationError(f"Title must be string, got {type(title)}")
    
    title = title.strip()
    if not title:
        raise ValidationError("Title cannot be empty")
    
    if len(title) > cfg.MAX_TITLE_LENGTH:
        raise ValidationError(
            f"Title too long (max {cfg.MAX_TITLE_LENGTH} chars): {title}"
        )
    
    # Validate editor
    if not isinstance(edited_by, str):
        raise ValidationError(f"Editor name must be string, got {type(edited_by)}")
    
    edited_by = edited_by.strip()
    if len(edited_by) > cfg.MAX_EDITOR_LENGTH:
        raise ValidationError(
            f"Editor name too long (max {cfg.MAX_EDITOR_LENGTH} chars): {edited_by}"
        )
    
    # Validate body
    if not isinstance(body, str):
        raise ValidationError(f"Body must be string, got {type(body)}")
    
    body = body.strip()
    if not body:
        raise ValidationError("Chapter body cannot be empty")
    
    # Check body size
    body_size_mb = len(body.encode('utf-8')) / (1024 * 1024)
    if body_size_mb > cfg.MAX_CHAPTER_SIZE_MB:
        raise ValidationError(
            f"Chapter too large ({body_size_mb:.1f}MB, max {cfg.MAX_CHAPTER_SIZE_MB}MB)"
        )
    
    logger.debug(f"Validated chapter {chapter_num}: {title}")
    return chapter_num, title, edited_by, body


def sanitize_csv_field(field: str, max_length: int = None) -> str:
    """
    Sanitize a CSV field to prevent CSV injection attacks.
    CSV injection: =malicious_formula, +command, etc.
    
    Args:
        field: CSV field value
        max_length: Optional maximum length
    
    Returns:
        Sanitized field safe for CSV
    """
    if not isinstance(field, str):
        field = str(field)
    
    # Escape dangerous CSV injection characters
    dangerous_chars = ('=', '+', '-', '@', '\t', '\r')
    if field and field[0] in dangerous_chars:
        field = "'" + field  # Prefix with quote to neutralize
    
    # Limit length if specified
    if max_length and len(field) > max_length:
        field = field[:max_length]
    
    return field


def sanitize_csv_row(row: list, max_field_length: int = 10000) -> list:
    """
    Sanitize an entire CSV row.
    
    Args:
        row: List of CSV fields
        max_field_length: Maximum length per field
    
    Returns:
        Sanitized row
    """
    return [sanitize_csv_field(str(field), max_field_length) for field in row]


def escape_csv_for_write(title: str, edited_by: str, body: str) -> Tuple[str, str, str]:
    """
    Properly escape CSV fields using csv.writer to prevent injection.
    
    Args:
        title: Chapter title
        edited_by: Editor name
        body: Chapter body
    
    Returns:
        Tuple of properly escaped (title, edited_by, body)
    """
    # Use csv.writer to handle escaping properly
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow([title, edited_by, body])
    
    escaped = output.getvalue().strip()
    # Parse back to get individual escaped fields
    reader = csv.reader(io.StringIO(escaped))
    row = next(reader)
    
    return row[0], row[1], row[2]


# ============================================================================
# URL VALIDATION
# ============================================================================

def validate_url(url: str) -> str:
    """
    Validate that a URL is well-formed.
    
    Args:
        url: URL string to validate
    
    Returns:
        Validated URL
    
    Raises:
        ValidationError: If URL is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")
    
    try:
        parsed = urlparse(url)
        
        if not parsed.scheme in ('http', 'https'):
            raise ValidationError(f"Invalid URL scheme: {parsed.scheme}")
        
        if not parsed.netloc:
            raise ValidationError("URL missing domain")
        
        return url.strip()
    
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {str(e)}")


def validate_domain(url: str) -> str:
    """
    Extract and validate domain from URL.
    
    Args:
        url: URL to validate
    
    Returns:
        Domain name
    
    Raises:
        ValidationError: If domain is invalid
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Domain must have at least one dot (except localhost)
        if domain != 'localhost' and '.' not in domain:
            raise ValidationError(f"Invalid domain format: {domain}")
        
        return domain
    except Exception as e:
        raise ValidationError(f"Cannot validate domain: {str(e)}")


# ============================================================================
# API KEY VALIDATION
# ============================================================================

def validate_api_key(api_key: str, api_name: str = "API") -> str:
    """
    Basic validation of API key format.
    
    Args:
        api_key: API key string
        api_name: Name of the API (for error messages)
    
    Returns:
        Validated API key
    
    Raises:
        ValidationError: If API key is invalid
    """
    if not api_key or not isinstance(api_key, str):
        raise ValidationError(f"{api_name} key must be a non-empty string")
    
    api_key = api_key.strip()
    
    if len(api_key) < 10:
        raise ValidationError(f"{api_name} key appears too short")
    
    # Check for obviously invalid characters
    if ' ' in api_key:
        raise ValidationError(f"{api_name} key contains spaces")
    
    return api_key


# ============================================================================
# BATCH VALIDATION
# ============================================================================

def validate_chapter_list(chapter_numbers: list) -> list:
    """
    Validate a list of chapter numbers.
    
    Args:
        chapter_numbers: List of chapter numbers
    
    Returns:
        Validated and sorted list
    
    Raises:
        ValidationError: If list is invalid
    """
    if not isinstance(chapter_numbers, (list, tuple, set)):
        raise ValidationError("Chapter list must be a list, tuple, or set")
    
    validated = set()
    for num in chapter_numbers:
        if not isinstance(num, int):
            raise ValidationError(f"Chapter number must be integer: {num}")
        
        if not (cfg.MIN_CHAPTER_NUMBER <= num <= cfg.MAX_CHAPTER_NUMBER):
            raise ValidationError(f"Chapter number out of range: {num}")
        
        validated.add(num)
    
    return sorted(validated)


# ============================================================================
# MANIFEST/STATE VALIDATION
# ============================================================================

def validate_manifest(manifest: dict) -> dict:
    """
    Validate the manifest JSON structure.
    
    Args:
        manifest: Manifest dictionary
    
    Returns:
        Validated manifest
    
    Raises:
        ValidationError: If manifest is invalid
    """
    required_fields = ['version', 'novel_name', 'chapters', 'last_updated']
    
    for field in required_fields:
        if field not in manifest:
            raise ValidationError(f"Manifest missing required field: {field}")
    
    if not isinstance(manifest['chapters'], dict):
        raise ValidationError("Manifest chapters must be a dictionary")
    
    return manifest