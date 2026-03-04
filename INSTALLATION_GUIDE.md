# NovelForge Windows Standalone - Complete Setup & Migration Guide

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [File Structure](#file-structure)
3. [Installation Steps](#installation-steps)
4. [Migration from Old Version](#migration-from-old-version)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [Testing](#testing)

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.8+ installed on Windows
- pip package manager
- ~100 MB disk space
- Internet connection (for API calls)

### Install & Run
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Get Google Gemini API key (free)
#    Visit: https://aistudio.google.com/app/apikey

# 3. Run the application
python main.py

# 4. Follow on-screen prompts
```

---

## 📁 File Structure

```
novelforge/
├── main.py                      # ✅ FIXED - Main entry point
├── config.py                    # ✨ NEW - Centralized configuration
├── utils.py                     # ✅ FIXED - Enhanced utilities
├── error_handler.py             # ✨ NEW - Exception handling
├── validators.py                # ✨ NEW - Input validation
├── manifest_manager.py          # ✨ NEW - State persistence
├── settings_manager.py          # ✅ FIXED - Settings persistence
├── enhancer.py                  # ✅ FIXED - AI enhancement (COMPLETE)
├── compiler.py                  # ✅ FIXED - EPUB generation
├── base_crawler.py              # ✅ FIXED - Base crawler class
│
├── crawlers/
│   ├── __init__.py             # ✨ NEW - Package init
│   └── xiaxuenovels.py         # ✅ FIXED - XiaXue crawler
│
├── requirements.txt             # ✅ UPDATED - All dependencies
└── README.md                    # ✅ UPDATED - Documentation

# Generated at runtime:
~\NovelForge\
├── config/
│   └── settings.json           # Settings file
├── data/
├── logs/
│   └── novelforge.log         # Application log
├── novels/
│   ├── my-novel-1/            # Novel output folder
│   │   ├── chapter_0001.csv
│   │   ├── chapter_0002.csv
│   │   └── my_novel_1.epub
│   └── .manifest/
│       └── my-novel-1.manifest.json  # State tracking
```

---

## ⚙️ Installation Steps

### Step 1: Prepare Your System

```bash
# Verify Python version
python --version
# Should be Python 3.8 or higher

# Create a working directory
mkdir novelforge
cd novelforge
```

### Step 2: Copy Fixed Files

Copy all the provided Python files to your `novelforge/` directory:

```
novelforge/
  ├── main.py
  ├── config.py
  ├── utils.py
  ├── error_handler.py
  ├── validators.py
  ├── manifest_manager.py
  ├── settings_manager.py
  ├── enhancer.py
  ├── compiler.py
  ├── base_crawler.py
  ├── requirements.txt
  └── crawlers/
      ├── __init__.py
      └── xiaxuenovels.py
```

### Step 3: Install Dependencies

```bash
# Windows (Command Prompt)
cd novelforge
pip install -r requirements.txt

# Or, if using PowerShell
pip install -r requirements.txt
```

**If you encounter errors:**
- Update pip: `python -m pip install --upgrade pip`
- Check Python path: `where python`
- For permission errors: Run Command Prompt as Administrator

### Step 4: Verify Installation

```bash
# Test imports
python -c "import requests; import beautifulsoup4; import ebooklib; print('✓ OK')"

# Check Google API
python -c "from google import genai; print('✓ OK')"

# Check rich UI
python -c "from rich.console import Console; print('✓ OK')"
```

### Step 5: Configure API Key

Get a free Google Gemini API key:

1. Visit: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Run: `python main.py`
5. When prompted, enter your API key
6. Settings will be saved automatically

### Step 6: First Run

```bash
python main.py
```

You should see:
```
✨ NovelForge ✨
Universal Light Novel Scraper & Enhancer

📖 Novel Setup
Enter the URL of the first chapter: https://xiaxuenovels.xyz/...
```

---

## 🔄 Migration from Old Version

### If You Have an Existing Installation

#### Option 1: Clean Migration (Recommended)

```bash
# 1. Backup your existing novels
xcopy novels ..\backup-novels /E /I

# 2. Delete old files
cd novelforge
del *.py  # Delete all old Python files

# 3. Copy new files from outputs folder
# Copy all fixed files here

# 4. Reinstall dependencies
pip install --upgrade -r requirements.txt

# 5. Run with new code
python main.py
```

#### Option 2: In-Place Update (Keep Settings)

```bash
# 1. Backup entire directory
xcopy novelforge ..\backup-novelforge /E /I

# 2. Replace individual files one by one
# Replace enhancer.py, compiler.py, utils.py, etc.
# Keep novels/ folder intact

# 3. Test each operation
python main.py  # Start here

# 4. Test crawling (Option 2)
# Test enhancement (Option 4)
# Test compilation (Option 5)
```

### Recovering Your Settings

Your old settings are stored in: `%USERPROFILE%\NovelForge\config\settings.json`

They will automatically be loaded by the new version:
- API key ✓
- Cleanup mode ✓
- AI model ✓

### Recovering Your Novels

Your downloaded chapters are in: `%USERPROFILE%\NovelForge\novels\`

The new version adds manifest files (`.manifest/`) but doesn't touch your CSV files:
- All chapter_*.csv files preserved ✓
- Can resume crawling from last chapter ✓
- Can re-enhance with new code ✓
- Can recompile EPUBs ✓

---

## ⚙️ Configuration

### API Key Management

**Option 1: UI Configuration (Easiest)**
```
Run: python main.py
Select: [6] ⚙️  Settings
Select: [1] 🔑 Set/Update API Key
Enter key
```

**Option 2: Environment Variable**
```bash
# Windows Command Prompt
set GOOGLE_API_KEY=your_key_here
python main.py

# Windows PowerShell
$env:GOOGLE_API_KEY="your_key_here"
python main.py
```

**Option 3: Direct File Edit**
```
File: %USERPROFILE%\NovelForge\config\settings.json

{
  "GOOGLE_API_KEY": "your_key_here",
  "AI_MODEL": "gemini-2.5-flash",
  "CLEANUP_MODE": "Ask",
  ...
}
```

### Tuning Performance

Edit `config.py` for site-specific optimization:

```python
# Crawler delays (xiaxuenovels.xyz can handle 1-2 seconds)
CRAWLER_DELAY_MIN = 1.0
CRAWLER_DELAY_MAX = 2.0

# API rate limiting
ENHANCEMENT_BATCH_DELAY = 2.0  # Delay between API calls

# Retry behavior
CRAWLER_MAX_RETRIES = 3
GEMINI_MAX_RETRIES = 3

# Logging
LOG_LEVEL = "INFO"  # DEBUG for more detail
```

---

## 🔧 Troubleshooting

### ImportError: No module named 'google'

**Solution:**
```bash
pip install google-genai
```

### ImportError: No module named 'requests'

**Solution:**
```bash
pip install requests beautifulsoup4 ebooklib
```

### 404 errors for all chapters

**Causes:**
- Wrong novel URL
- Website changed structure
- Paywall enforcement

**Solution:**
- Verify URL format: `https://xiaxuenovels.xyz/novel-slug/chapter-1`
- Use browser to manually test the URL
- Check logs: `%USERPROFILE%\NovelForge\logs\novelforge.log`

### API key rejected

**Solution:**
1. Verify key at: https://aistudio.google.com/app/apikey
2. Check for extra spaces: `key.strip()`
3. Regenerate key if necessary
4. Update via UI [6] → [1]

### Out of memory with large novels

**Solution:**
- Process in batches: Run enhancement on 50 chapters at a time
- Use Debug mode: Set `LOG_LEVEL = "DEBUG"` to monitor memory
- Reduce BATCH_SIZE: Set to 1 in config.py

### CSV files won't load

**Cause:** Corrupt or invalid CSV format

**Solution:**
1. Check file in Excel or text editor
2. Look for missing values in columns
3. For damaged files, delete and re-crawl
4. Use manifest to identify: `cat .manifest/novel-slug.manifest.json`

### EPUB won't open in reader

**Cause:** Invalid HTML or missing chapters

**Solution:**
1. Run validation: `python compiler.py` (after updating with test code)
2. Check compile log for errors
3. Verify all chapters have body content
4. Try opening in Calibre (free tool) for better error messages

---

## 🧪 Testing

### Unit Tests (Optional)

```bash
# Create test_novelforge.py
python -m pytest test_novelforge.py -v
```

### Manual Testing Checklist

```
[ ] 1. Application starts: python main.py
[ ] 2. Can enter novel URL
[ ] 3. Settings save/load correctly
[ ] 4. API key configured
[ ] 5. Can start crawling (10 chapters)
[ ] 6. Can interrupt (CTRL+C) and resume
[ ] 7. Can run enhancement (check limits first!)
[ ] 8. EPUB compiles without errors
[ ] 9. All chapters in EPUB
[ ] 10. EPUB opens in reader
```

### Debug Mode

```bash
# Run with detailed logging
python -c "
import config
config.LOG_LEVEL = 'DEBUG'
exec(open('main.py').read())
"
```

---

## 📞 Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `ConnectionError` | Network issue | Check internet, retry |
| `TimeoutError` | Server slow | Increase delay in config.py |
| `404 Not Found` | Chapter doesn't exist | URL structure changed |
| `403 Forbidden` | Paywall/blocking | Crawler detects paywalls |
| `APIError: 429` | Rate limit exceeded | Wait and retry, reduce batch size |
| `FileNotFoundError` | Missing chapter CSV | Re-crawl chapters |
| `UnicodeDecodeError` | Encoding issue | Fixed in new utils.py |

---

## 📊 Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| Crawl 100 chapters | 5-10 min | 1-3 sec delay per chapter |
| Enhance 100 chapters | 10-20 min | Depends on API speed |
| Compile EPUB | 10-30 sec | Depends on chapter count |
| Full pipeline 100 ch | 30-50 min | With enhancement |

---

## 🚀 Advanced Usage

### Bulk Processing

```bash
# Process multiple novels
for /L %i in (1,1,10) do python main.py
```

### Scripted Automation

```bash
# create_novel.bat
@echo off
python main.py
```

Then schedule with Windows Task Scheduler.

### Custom Crawlers

See `CONTRIBUTION.md` for adding support for new websites.

---

## 📝 Logging

Logs are saved to: `%USERPROFILE%\NovelForge\logs\novelforge.log`

View current session:
```bash
type %USERPROFILE%\NovelForge\logs\novelforge.log | tail -20
```

Or from PowerShell:
```powershell
Get-Content "$env:USERPROFILE\NovelForge\logs\novelforge.log" -Tail 20
```

---

## ✅ Verification Checklist

Before considering the installation complete:

- [ ] All files copied to novelforge/
- [ ] `pip install -r requirements.txt` succeeded
- [ ] `python main.py` starts without errors
- [ ] UI displays correctly (colors, panels)
- [ ] Can enter novel URL
- [ ] Settings save/load
- [ ] API key configured
- [ ] Can start and interrupt crawling
- [ ] Can run full pipeline
- [ ] EPUB compiles and opens

---

## 📚 Additional Resources

- **Google AI Studio:** https://aistudio.google.com/
- **Python Documentation:** https://docs.python.org/3/
- **BeautifulSoup Docs:** https://www.crummy.com/software/BeautifulSoup/
- **EPUB Standard:** https://www.w3.org/publishing/epub/

---

## 🆘 Still Having Issues?

1. Check `novelforge.log` for error messages
2. Test imports individually
3. Verify all files copied correctly
4. Reinstall in clean Python environment
5. Report issues with logs attached

---

**Last Updated:** March 2026  
**Version:** 2.0 (Complete Overhaul)  
**Windows Compatibility:** Windows 10/11
