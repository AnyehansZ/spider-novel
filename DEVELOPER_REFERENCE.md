# NovelForge Developer Quick Reference

## 🚀 Quick Commands

```bash
# Install
pip install -r requirements.txt

# Run
python main.py

# Debug (verbose logging)
python -c "import config; config.LOG_LEVEL='DEBUG'" && python main.py

# View logs
type %USERPROFILE%\NovelForge\logs\novelforge.log

# Test crawler only
python -c "from crawlers.xiaxuenovels import *; XiaXueCrawler(...).run_crawler()"

# Extract manifest
python -c "from manifest_manager import *; m = ManifestManager().load_manifest('slug'); print(m.to_dict())"
```

---

## 📦 Module Quick Reference

### Core Modules

| Module | Purpose | Key Classes | Import |
|--------|---------|------------|--------|
| `config.py` | Constants | - | `import config as cfg` |
| `error_handler.py` | Exceptions | `ErrorContext`, `ErrorSummary` | `from error_handler import *` |
| `validators.py` | Validation | - | `import validators` |
| `manifest_manager.py` | State | `NovelManifest`, `ManifestManager` | `from manifest_manager import *` |
| `utils.py` | Utilities | `SimpleProgress` | `import utils` |
| `settings_manager.py` | Config | `SettingsManager` | `from settings_manager import *` |

### Business Logic

| Module | Purpose | Key Classes | Import |
|--------|---------|------------|--------|
| `base_crawler.py` | Crawler Base | `BaseCrawler` | `from base_crawler import BaseCrawler` |
| `xiaxuenovels.py` | XiaXue Crawler | `XiaXueCrawler` | `from crawlers.xiaxuenovels import XiaXueCrawler` |
| `enhancer.py` | AI Enhancement | `EnhanceAPI`, `BatchEnhancer` | `from enhancer import *` |
| `compiler.py` | EPUB Compiler | `EPUBCompiler` | `from compiler import EPUBCompiler` |
| `main.py` | CLI Entry | `NovelForgeApp` | `python main.py` |

---

## 🔧 Common Patterns

### Error Handling

```python
# Pattern 1: Context manager
from error_handler import ErrorContext

with ErrorContext("operation name", raise_on_error=True) as ctx:
    risky_operation()
# Logs error and optionally re-raises

# Pattern 2: Retry decorator
from error_handler import retry_with_backoff

@retry_with_backoff(max_attempts=3, exceptions=(TimeoutError,))
def fetch_data(url):
    return requests.get(url)

# Pattern 3: Error summary
from error_handler import ErrorSummary

summary = ErrorSummary("batch operation")
for item in items:
    try:
        process(item)
        summary.record_success()
    except Exception as e:
        summary.add_error(item.id, e)

print(summary.get_report())
```

### Validation

```python
# Validate URLs
from validators import validate_url, validate_domain
url = validate_url(user_input)  # Raises ValidationError if invalid
domain = validate_domain(url)

# Validate paths
from validators import validate_output_path, ensure_safe_directory
safe_path = validate_output_path(base=cfg.NOVELS_DIR, relative="user-input")
safe_dir = ensure_safe_directory(path, create=True)

# Validate data
from validators import validate_chapter_data
ch_num, title, editor, body = validate_chapter_data(
    chapter_num, title, editor, body
)  # Raises ValidationError if invalid
```

### Manifest Management

```python
from manifest_manager import ManifestManager, ChapterRecord

manager = ManifestManager()

# Load
manifest = manager.load_manifest("novel-slug")

# Create
manifest = manager.create_manifest(
    "Novel Name", Path("output"), "novel-slug"
)

# Update chapter
record = manifest.get_chapter(1)
manifest.mark_downloaded(1, url="...", content_hash="...")
manifest.mark_enhanced(1)
manifest.mark_error(2, "Error message")

# Save
manager.save_manifest(manifest, "novel-slug")

# Query
missing = manifest.get_missing_chapters(100)
chapters = manifest.get_chapters_by_status("enhanced")
```

### Settings Management

```python
from settings_manager import SettingsManager

settings = SettingsManager()

# Get values
api_key = settings.get_api_key()
model = settings.get_model()
cleanup_mode = settings.get_cleanup_mode()

# Set values
settings.set_api_key("key...")
settings.set_model("gemini-2.5-flash")
settings.set_cleanup_mode("Ask")

# Validate
if settings.validate():
    print("All settings OK")
```

### File Operations

```python
from utils import (
    ensure_folder, save_chapter_to_csv, load_chapter_from_csv,
    update_chapter_csv, get_downloaded_chapters
)

# Ensure folder exists
folder = ensure_folder(Path("novels/my-novel"))

# Save chapter
success = save_chapter_to_csv(
    folder, chapter_num=1, title="Chapter 1",
    edited_by="TL", body_text="...", enhanced="False"
)

# Load chapter
result = load_chapter_from_csv(Path("novels/my-novel/chapter_0001.csv"))
if result:
    title, editor, body, enhanced = result

# Update chapter
success = update_chapter_csv(
    Path("novels/my-novel/chapter_0001.csv"),
    body_text=new_body,
    enhanced="True"
)

# Get downloaded chapters
chapters = get_downloaded_chapters(Path("novels/my-novel"))
# Returns: [1, 2, 3, 5, 6, ...]  (note: missing 4)
```

---

## 🎯 Creating a New Crawler

```python
# File: crawlers/newsite.py
from base_crawler import BaseCrawler
from error_handler import InvalidChapterDataError
import utils
from bs4 import BeautifulSoup

class NewSiteCrawler(BaseCrawler):
    def __init__(self, novel_name, output_folder, base_url, start_url):
        super().__init__(novel_name, output_folder, base_url, start_url)
        # Custom initialization
    
    def _parse_chapter(self, soup: BeautifulSoup) -> tuple:
        """Extract (title, edited_by, body) from HTML."""
        try:
            title = soup.find('h1', class_='title').text.strip()
            editor = "Unknown"
            body_div = soup.find('div', class_='content')
            body = "\n".join(p.text for p in body_div.find_all('p'))
            
            return title, editor, body
        except Exception as e:
            raise InvalidChapterDataError(f"Parse error: {str(e)}")
    
    def _extract_next_link(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract URL to next chapter."""
        next_btn = soup.find('a', class_='next')
        return next_btn.get('href') if next_btn else None
    
    def run_crawler(self):
        """Main crawl loop."""
        # See xiaxuenovels.py for complete implementation
        pass
    
    def check_and_fix_missing(self):
        """Recover missing chapters."""
        # See xiaxuenovels.py for complete implementation
        pass

# Register in main.py:
# CRAWLER_REGISTRY["newsite.com"] = NewSiteCrawler
```

---

## 🧪 Testing Patterns

```python
# Test validators
from validators import validate_url, ValidationError
import pytest

def test_valid_url():
    url = validate_url("https://example.com/chapter-1")
    assert url == "https://example.com/chapter-1"

def test_invalid_url():
    with pytest.raises(ValidationError):
        validate_url("not a url")

# Test crawler
from crawlers.xiaxuenovels import XiaXueCrawler
from pathlib import Path

def test_crawler_init():
    crawler = XiaXueCrawler(
        "Test Novel",
        Path("test_output"),
        "https://xiaxuenovels.xyz/test/",
        "chapter-1"
    )
    assert crawler.novel_name == "Test Novel"
    assert crawler.chapter_prefix == "chapter-"

# Test manifest
from manifest_manager import ManifestManager, ChapterRecord

def test_manifest_save_load():
    manager = ManifestManager()
    manifest = manager.create_manifest("Test", Path("output"), "test")
    
    record = ChapterRecord(1, "Chapter 1", "downloaded")
    manifest.add_chapter(record)
    manager.save_manifest(manifest, "test")
    
    loaded = manager.load_manifest("test")
    assert len(loaded.chapters) == 1
    assert loaded.chapters[1].title == "Chapter 1"
```

---

## 🔍 Debugging

### Enable Debug Logging

```python
# Option 1: via config
import config
config.LOG_LEVEL = "DEBUG"

# Option 2: via settings
from settings_manager import SettingsManager
settings = SettingsManager()
settings.set_log_level("DEBUG")
```

### View Logs

```bash
# Windows Command Prompt
type %USERPROFILE%\NovelForge\logs\novelforge.log

# PowerShell
Get-Content "$env:USERPROFILE\NovelForge\logs\novelforge.log" -Tail 50
```

### Inspect State

```python
# Check manifest state
from manifest_manager import ManifestManager, generate_manifest_report
manager = ManifestManager()
manifest = manager.load_manifest("novel-slug")
print(generate_manifest_report(manifest))

# Check settings
from settings_manager import SettingsManager
settings = SettingsManager()
print(f"API Key: {settings.has_api_key()}")
print(f"Model: {settings.get_model()}")
```

---

## 📊 Configuration Reference

```python
import config as cfg

# Paths
cfg.APP_DIR              # ~/NovelForge
cfg.NOVELS_DIR           # ~/NovelForge/novels
cfg.CONFIG_FILE          # ~/NovelForge/config/settings.json
cfg.LOG_FILE             # ~/NovelForge/logs/novelforge.log

# Crawler settings
cfg.CRAWLER_DELAY_MIN              # 1.0 seconds
cfg.CRAWLER_DELAY_MAX              # 3.0 seconds
cfg.CRAWLER_TIMEOUT                # 15 seconds
cfg.CRAWLER_MAX_RETRIES            # 3 attempts
cfg.CRAWLER_RETRY_BACKOFF          # 2.0x multiplier
cfg.CRAWLER_CONSECUTIVE_FAILS_LIMIT # 5 failures

# AI settings
cfg.GEMINI_API_TIMEOUT             # 60 seconds
cfg.GEMINI_MAX_RETRIES             # 3 attempts
cfg.GEMINI_BATCH_SIZE              # 1 chapter
cfg.ENHANCEMENT_BATCH_DELAY        # 2.0 seconds

# Validation limits
cfg.MAX_CHAPTER_SIZE_MB            # 10 MB
cfg.MAX_TITLE_LENGTH               # 200 chars
cfg.MAX_PATH_LENGTH                # 250 chars
```

---

## 🚀 Performance Tips

### Crawler Optimization
```python
# Faster for trusted sites
config.CRAWLER_DELAY_MIN = 0.5
config.CRAWLER_DELAY_MAX = 1.0

# Slower for rate-limited sites
config.CRAWLER_DELAY_MIN = 3.0
config.CRAWLER_DELAY_MAX = 5.0
```

### Enhancement Optimization
```python
# Reduce API calls (not recommended, may degrade quality)
config.SKIP_ALREADY_ENHANCED = True

# Faster, but hits rate limits
config.ENHANCEMENT_BATCH_DELAY = 1.0

# Safer, respects limits
config.ENHANCEMENT_BATCH_DELAY = 2.0
```

### Large Novel Handling
```python
# Process in batches of 50 chapters
# Update enhancement, verify with compiler
# Then process next 50

# Or use concurrent operations (advanced)
# from concurrent_crawler import AsyncCrawler
```

---

## 📋 Common Issues & Solutions

| Issue | Debug Steps | Solution |
|-------|------------|----------|
| Import Error | `python -c "import module"` | Check requirements, verify file exists |
| API Timeout | Check `LOG_LEVEL=DEBUG` | Increase timeout in config |
| Missing Chapters | Inspect manifest | Run `check_and_fix_missing()` |
| Corrupt CSV | Read file in editor | Re-crawl chapters |
| EPUB won't open | Check compiler log | Run validation first |

---

## 🔗 Important Classes

### BaseCrawler
```python
# Subclass this for new sites
class XiaXueCrawler(BaseCrawler):
    def _parse_chapter(soup) -> (title, editor, body)
    def _extract_next_link(soup) -> url_or_none
    def run_crawler()
    def check_and_fix_missing()
    
# Helpers
.save_chapter(chapter_num, title, editor, body, url)
.get_last_chapter_number()
.get_missing_chapters(max_chapter)
.fetch_with_retry(url)
```

### SettingsManager
```python
settings.get_api_key()
settings.set_api_key(key)
settings.get_model()
settings.set_model(model)
settings.get_cleanup_mode()
settings.set_cleanup_mode(mode)
settings.validate()
```

### ManifestManager
```python
manager.load_manifest(slug)
manager.save_manifest(manifest, slug)
manager.create_manifest(name, folder, slug)
manager.get_all_manifests()
```

### EPUBCompiler
```python
compiler.compile(output_filename, author, language)
compiler.get_error_summary()
```

---

## 🎓 Best Practices

1. **Always validate input**
   ```python
   validators.validate_chapter_data(...)
   validators.validate_url(...)
   validators.sanitize_filename(...)
   ```

2. **Use context managers for resources**
   ```python
   with ErrorContext("operation", raise_on_error=False):
       do_something()
   ```

3. **Check errors in manifests**
   ```python
   if manifest.crawl_state['consecutive_failures'] > 0:
       logger.warning("Crawl had errors")
   ```

4. **Test with small datasets first**
   ```python
   # Test with 5 chapters before full crawl
   manifest.get_chapters_by_status("downloaded")[:5]
   ```

5. **Log important state changes**
   ```python
   logger.info(f"Switched model to {new_model}")
   manifest.update_crawl_state(last_chapter=num)
   ```

---

## 📞 Reference Links

- **Python Logging:** https://docs.python.org/3/library/logging.html
- **Pathlib Guide:** https://docs.python.org/3/library/pathlib.html
- **BeautifulSoup:** https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **Google Genai:** https://ai.google.dev/tutorials/python_quickstart
- **ebooklib:** https://github.com/aerkalov/ebooklib

---

**Last Updated:** March 2026  
**Version:** 2.0  
**Status:** Production Ready ✅
