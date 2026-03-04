"""
NovelForge Error Handling Module
Custom exceptions, retry decorators, and error recovery mechanisms.
"""

import time
import functools
import logging
from typing import Callable, Any, Type, Tuple
from pathlib import Path

logger = logging.getLogger("NovelForge.ErrorHandler")


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class NovelForgeError(Exception):
    """Base exception for all NovelForge errors."""
    pass


class CrawlerError(NovelForgeError):
    """Base exception for crawler-related errors."""
    pass


class ChapterNotFoundError(CrawlerError):
    """Raised when a chapter cannot be found or accessed."""
    pass


class InvalidChapterDataError(CrawlerError):
    """Raised when chapter data is invalid or incomplete."""
    pass


class IncompleteChapterError(CrawlerError):
    """Raised when a chapter has no body content."""
    pass


class NetworkError(CrawlerError):
    """Raised for network-related failures."""
    pass


class TimeoutError(NetworkError):
    """Raised when a request times out."""
    pass


class RateLimitError(NetworkError):
    """Raised when API/server rate limit is hit."""
    pass


class PaywallError(CrawlerError):
    """Raised when content is behind a paywall."""
    pass


class EnhancerError(NovelForgeError):
    """Base exception for enhancer-related errors."""
    pass


class APIKeyError(EnhancerError):
    """Raised when API key is missing or invalid."""
    pass


class APIConnectionError(EnhancerError):
    """Raised when API connection fails."""
    pass


class APIRateLimitError(EnhancerError):
    """Raised when AI API rate limit is exceeded."""
    pass


class APIResponseError(EnhancerError):
    """Raised when AI API returns an error response."""
    pass


class CompilerError(NovelForgeError):
    """Base exception for EPUB compilation errors."""
    pass


class ValidationError(NovelForgeError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(NovelForgeError):
    """Raised for configuration issues."""
    pass


# ============================================================================
# RETRY DECORATOR WITH EXPONENTIAL BACKOFF
# ============================================================================

def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable = None,
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        backoff_factor: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Optional callback function(attempt, delay, exception)
    
    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(TimeoutError,))
        def fetch_chapter(url):
            return requests.get(url, timeout=10)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = base_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"[{func.__name__}] Attempt {attempt}/{max_attempts}")
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"[{func.__name__}] Failed after {max_attempts} attempts: {str(e)}"
                        )
                        raise
                    
                    # Calculate next delay with exponential backoff
                    delay = min(delay * backoff_factor, max_delay)
                    
                    # Call callback if provided
                    if on_retry:
                        on_retry(attempt, delay, e)
                    
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt} failed ({type(e).__name__}). "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception or NovelForgeError(f"Unknown error in {func.__name__}")
        
        return wrapper
    return decorator


# ============================================================================
# CONTEXT MANAGERS FOR ERROR HANDLING
# ============================================================================

class ErrorContext:
    """Context manager for graceful error handling with logging."""
    
    def __init__(
        self,
        operation_name: str,
        logger: logging.Logger = None,
        raise_on_error: bool = False,
        default_return: Any = None,
    ):
        """
        Args:
            operation_name: Name of the operation for logging
            logger: Logger instance (uses NovelForge logger if None)
            raise_on_error: If False, catches and logs errors; if True, re-raises
            default_return: Value to return if error occurs and raise_on_error=False
        """
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger("NovelForge")
        self.raise_on_error = raise_on_error
        self.default_return = default_return
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        
        self.error = exc_val
        
        # Log the error
        self.logger.error(
            f"[{self.operation_name}] {exc_type.__name__}: {str(exc_val)}"
        )
        
        # Decide whether to suppress or re-raise
        if self.raise_on_error:
            return False  # Re-raise the exception
        else:
            return True   # Suppress the exception


class SafeFileOperation:
    """Context manager for safe file operations with automatic cleanup on failure."""
    
    def __init__(self, file_path: Path, mode: str = 'r', encoding: str = 'utf-8'):
        self.file_path = Path(file_path)
        self.mode = mode
        self.encoding = encoding
        self.file_handle = None
        self.created = False
    
    def __enter__(self):
        try:
            self.file_handle = open(self.file_path, self.mode, encoding=self.encoding)
            self.created = 'w' in self.mode or 'a' in self.mode
            return self.file_handle
        except IOError as e:
            logger.error(f"Failed to open file {self.file_path}: {str(e)}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_handle:
            self.file_handle.close()
        
        # If write mode and an error occurred, delete the file
        if exc_type is not None and self.created and self.file_path.exists():
            try:
                self.file_path.unlink()
                logger.warning(f"Deleted incomplete file: {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to delete incomplete file {self.file_path}: {str(e)}")
        
        return False  # Don't suppress exceptions


# ============================================================================
# ERROR SUMMARY & REPORTING
# ============================================================================

class ErrorSummary:
    """Accumulates and reports errors from batch operations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.errors = []
        self.warnings = []
        self.successes = 0
    
    def add_error(self, chapter_id: Any, error: Exception, details: str = ""):
        """Record an error."""
        self.errors.append({
            "chapter_id": chapter_id,
            "error_type": type(error).__name__,
            "message": str(error),
            "details": details,
        })
    
    def add_warning(self, chapter_id: Any, message: str):
        """Record a warning."""
        self.warnings.append({
            "chapter_id": chapter_id,
            "message": message,
        })
    
    def record_success(self):
        """Record a successful operation."""
        self.successes += 1
    
    def get_report(self) -> str:
        """Generate a formatted error report."""
        total = self.successes + len(self.errors)
        lines = [
            f"\n{'='*60}",
            f"Operation: {self.operation_name}",
            f"{'='*60}",
            f"✓ Successful: {self.successes}/{total}",
            f"✗ Errors: {len(self.errors)}",
            f"⚠ Warnings: {len(self.warnings)}",
        ]
        
        if self.errors:
            lines.append("\nFailed Items:")
            for error in self.errors:
                lines.append(
                    f"  • Chapter {error['chapter_id']}: "
                    f"{error['error_type']} - {error['message']}"
                )
                if error['details']:
                    lines.append(f"    {error['details']}")
        
        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  • Chapter {warning['chapter_id']}: {warning['message']}")
        
        lines.append(f"{'='*60}\n")
        return "\n".join(lines)
    
    def save_report(self, file_path: Path):
        """Save the error report to a file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.get_report())
        
        logger.info(f"Error report saved to {file_path}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_transient_error(exception: Exception) -> bool:
    """
    Determine if an error is transient (retry-worthy) or permanent.
    
    Transient errors: Timeout, ConnectionError, RateLimitError
    Permanent errors: ValidationError, PaywallError, FileNotFoundError
    """
    transient_types = (
        TimeoutError,
        NetworkError,
        RateLimitError,
        APIConnectionError,
        APIRateLimitError,
        ConnectionError,
    )
    
    permanent_types = (
        ValidationError,
        PaywallError,
        FileNotFoundError,
        PermissionError,
        ConfigurationError,
        APIKeyError,
    )
    
    if isinstance(exception, permanent_types):
        return False
    
    if isinstance(exception, transient_types):
        return True
    
    # Default: treat as transient (safer to retry)
    return True


def format_error_for_logging(exception: Exception, context: str = "") -> str:
    """Format an exception for clear logging."""
    msg = f"{type(exception).__name__}: {str(exception)}"
    if context:
        msg = f"[{context}] {msg}"
    return msg