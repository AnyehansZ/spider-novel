"""
NovelForge Configuration Constants
Centralized configuration for the entire application.
All magic numbers and constants defined here for easy tuning.
"""

import os
from pathlib import Path

# ============================================================================
# APPLICATION PATHS
# ============================================================================

# Base directory for the application
APP_DIR = Path.home() / "NovelForge"  # Windows-friendly: C:\Users\YourUser\NovelForge
DATA_DIR = APP_DIR / "data"
NOVELS_DIR = APP_DIR / "novels"
LOGS_DIR = APP_DIR / "logs"
CONFIG_DIR = APP_DIR / "config"

# Config files
CONFIG_FILE = CONFIG_DIR / "settings.json"
MANIFEST_DIR = NOVELS_DIR / ".manifest"  # Hidden folder for manifests

# Ensure all directories exist
for dir_path in [APP_DIR, DATA_DIR, NOVELS_DIR, LOGS_DIR, CONFIG_DIR, MANIFEST_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Log file
LOG_FILE = LOGS_DIR / "novelforge.log"

# ============================================================================
# CRAWLER SETTINGS
# ============================================================================

# Default crawler delays (in seconds)
CRAWLER_DELAY_MIN = 1.0              # Minimum delay between requests
CRAWLER_DELAY_MAX = 3.0              # Maximum delay between requests (random)
CRAWLER_TIMEOUT = 15                 # Request timeout in seconds
CRAWLER_MAX_RETRIES = 3              # Max retry attempts for failed chapters
CRAWLER_RETRY_BACKOFF = 2.0          # Exponential backoff multiplier
CRAWLER_CONSECUTIVE_FAILS_LIMIT = 5  # Stop crawling after N consecutive 404s

# User Agent for requests
CRAWLER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ============================================================================
# AI ENHANCEMENT SETTINGS
# ============================================================================

# Gemini API Configuration
GEMINI_API_TIMEOUT = 60              # API request timeout (seconds)
GEMINI_MAX_RETRIES = 3               # Retry failed API calls
GEMINI_RETRY_DELAY = 2.0             # Delay between retries (seconds)
GEMINI_BATCH_SIZE = 1                # Chapters per batch (1 = safest, higher = faster but riskier)
GEMINI_TEMPERATURE = 0.7             # Model temperature (0-1, lower = more consistent)
GEMINI_MAX_TOKENS = 4000             # Max tokens in response

# Default model options
DEFAULT_AI_MODEL = "gemini-2.5-flash"  # Options: gemini-2.0-flash, gemini-2.5-flash, gemini-1.5-pro
AVAILABLE_AI_MODELS = {
    "gemini-3.0-flash": "Flash 3.0 (Fastest, Newest)",
    "gemini-2.5-flash": "Flash 2.5 (Stable, Recommended)",
    "gemini-2.0-flash": "Flash 2.0 (Legacy)",
}

# Enhancement settings
ENHANCEMENT_BATCH_DELAY = 2.0        # Delay between API calls (rate limiting)
SKIP_ALREADY_ENHANCED = True         # Skip chapters marked as enhanced
ENHANCEMENT_PROMPT_TEMPLATE = """
Fix the machine-translated novel text below. Improve grammar, clarity, and natural phrasing while preserving the original meaning and intent. Do not add or remove content.

Text:
{body}

Return ONLY the improved text, no explanations.
"""

# ============================================================================
# COMPILER/EPUB SETTINGS
# ============================================================================

EPUB_DEFAULT_LANGUAGE = "en"
EPUB_DEFAULT_AUTHOR = "Unknown"
EPUB_TITLE_TEMPLATE = "{novel_name}.epub"

# CSS styling for EPUB
EPUB_STYLESHEET = """
@namespace url("http://www.w3.org/1999/xhtml");

body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 1em;
    text-align: justify;
    color: #222;
}

h1 {
    text-align: center;
    margin-bottom: 0.5em;
    font-size: 1.8em;
    page-break-before: always;
    color: #1a1a1a;
}

h2 {
    text-align: center;
    margin-top: 1em;
    font-size: 1.3em;
}

p {
    text-indent: 1.5em;
    margin-bottom: 0.5em;
}

p.author-note {
    font-style: italic;
    text-indent: 0;
    margin: 1em 0;
    color: #666;
}

.chapter-separator {
    text-align: center;
    margin: 1.5em 0;
    color: #999;
}
"""

# ============================================================================
# VALIDATION & SECURITY
# ============================================================================

# Max file sizes
MAX_CHAPTER_SIZE_MB = 10              # Max size of a single chapter
MAX_TITLE_LENGTH = 200                # Max chapter title length
MAX_EDITOR_LENGTH = 100               # Max editor name length

# Valid chapter number range
MIN_CHAPTER_NUMBER = 0
MAX_CHAPTER_NUMBER = 99999

# Path sanitization
FORBIDDEN_CHARS_PATH = r'<>:"|?*\\'  # Windows forbidden filename chars
MAX_PATH_LENGTH = 250                 # Leave room for Windows limit of 260

# ============================================================================
# SETTINGS/STATE MANAGEMENT
# ============================================================================

# Cleanup behavior options
CLEANUP_MODES = {
    "Always": "Delete raw CSV files automatically after EPUB compilation",
    "Ask": "Prompt user each time before deleting",
    "Never": "Keep all CSV files",
}
DEFAULT_CLEANUP_MODE = "Ask"

# Resume behavior
RESUME_FROM_LAST = True               # Auto-resume from last chapter
MANIFEST_AUTO_SAVE = True             # Auto-save crawl state

# ============================================================================
# LOGGING
# ============================================================================

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = "INFO"                    # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Rotating log file settings
LOG_MAX_BYTES = 5 * 1024 * 1024      # 5 MB
LOG_BACKUP_COUNT = 3                 # Keep 3 backup log files

# ============================================================================
# UI/UX SETTINGS (Windows Terminal)
# ============================================================================

# Whether to use rich formatting (set to False on minimal terminals)
ENABLE_RICH_FORMATTING = True

# Progress bar update frequency
PROGRESS_UPDATE_INTERVAL = 0.5        # seconds

# Spinner animation
SPINNER_TYPE = "dots"                 # dots, line, dots2, dots3, dots4, dots5, dots6, dots7, dots8, dots9

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# Concurrent processing (for future async implementation)
MAX_CONCURRENT_DOWNLOADS = 3          # Parallel download threads/coroutines
MAX_CONCURRENT_API_CALLS = 1          # Keep low to respect rate limits
CHUNK_SIZE = 8192                     # Bytes for streaming downloads

# CSV handling
CSV_ENCODING = "utf-8"
CSV_DIALECT = "excel"
CSV_QUOTING = "minimal"

# ============================================================================
# FEATURE FLAGS
# ============================================================================

ENABLE_ASYNC_CRAWLER = False          # Use experimental async crawler
ENABLE_COMPRESSION = False            # Compress chapter data in manifest
ENABLE_METRICS = True                 # Track performance metrics
ENABLE_AUTO_UPDATE = False            # Check for app updates (future)

# ============================================================================
# DEFAULTS
# ============================================================================

DEFAULT_SETTINGS = {
    "GOOGLE_API_KEY": "",
    "CLEANUP_MODE": DEFAULT_CLEANUP_MODE,
    "AI_MODEL": DEFAULT_AI_MODEL,
    "CRAWLER_DELAY_MIN": CRAWLER_DELAY_MIN,
    "CRAWLER_DELAY_MAX": CRAWLER_DELAY_MAX,
    "ENABLE_LOGGING": True,
    "LOG_LEVEL": LOG_LEVEL,
}