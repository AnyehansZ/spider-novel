# NovelForge ✨

**Universal Light Novel Scraper, AI Enhancer & EPUB Compiler**

Automatically crawl web novels, fix machine-translated (MTL) text with AI, and compile beautifully formatted eBooks.

## ✨ Features

- **Modular Crawler System** - Add support for any light novel website with a single Python class
- **AI Text Enhancement** - Uses Google Gemini API to naturally rewrite poor translations while preserving meaning
- **Smart Recovery** - Automatically detects missing chapters and attempts to bypass paywalls/broken links
- **Resumable Operations** - Pause and resume at any time. Progress is saved in standard CSV format
- **One-Click EPUB Compilation** - Creates professionally formatted eBooks with automatic Table of Contents
- **Enterprise-Grade Error Handling** - Comprehensive logging, retry logic, and recovery mechanisms
- **Multi-Platform Support** - Windows, Linux, macOS with identical behavior

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/novelforge.git
cd novelforge

# Install dependencies
pip install -r requirements.txt

# Set API key
export GOOGLE_API_KEY="your_gemini_api_key_here"  # Linux/Mac
set GOOGLE_API_KEY=your_gemini_api_key_here       # Windows
```

### Usage

```bash
python main.py
```

You'll see a menu:
```
[1] 🚀 Run Full Auto-Pipeline (Crawl → Fix → Enhance → EPUB)
[2] 🕸️  Start / Resume Crawling
[3] 🛠️  Check and Fix Missing Chapters
[4] ✨ Enhance Downloaded CSVs (Gemini AI)
[5] 📚 Compile CSVs to EPUB
[0] ❌ Exit
```

**Example:** Enter URL: `https://xiaxuenovels.xyz/my-novel/chapter-1`

## 📚 Supported Sites

Currently supported:
- **XiaXue Novels** (xiaxuenovels.xyz)

Easy to add more! See [Contributing](#contributing).

## 📂 Project Structure

```
novelforge/
├── main.py                 # Main CLI application
├── config.py              # Configuration management
├── utils.py               # Utility functions
├── error_handler.py       # Custom exceptions & error handling
├── validators.py          # Input validation
├── manifest_manager.py    # State persistence
├── settings_manager.py    # User preferences
├── enhancer.py            # Google Gemini API integration
├── compiler.py            # EPUB generation (ebooklib)
├── compiler_pypub.py      # Alternative EPUB generator (pypub)
│
├── crawlers/
│   ├── base_crawler.py    # Abstract base class
│   └── xiaxuenovels.py    # XiaXue Novels crawler
│
├── .github/workflows/     # GitHub Actions CI/CD
│   ├── ci.yml            # Testing & linting
│   ├── release.yml       # Windows EXE builds
│   └── security.yml      # Security scanning
│
└── novels/                # Output directory (auto-created)
    └── novel-slug/
        ├── chapter_0001.csv
        ├── chapter_0002.csv
        └── ...
```

## 🛠️ Adding a New Crawler

Create `crawlers/mynewsite.py`:

```python
from crawlers.base_crawler import BaseCrawler
import utils

class MyNewSiteCrawler(BaseCrawler):
    def __init__(self, novel_name, output_folder, base_url, start_url):
        super().__init__(novel_name, output_folder, base_url, start_url)
        self.headers = {"User-Agent": "Mozilla/5.0..."}

    def _parse_chapter(self, soup):
        """Extract title, editor, and body from page."""
        title = soup.find('h1').text
        edited_by = "Unknown"
        body = "\n".join([p.text for p in soup.find_all('p')])
        return title, edited_by, body

    def _extract_next_link(self, soup):
        """Find next chapter link."""
        return soup.find('a', rel='next')['href'] if soup.find('a', rel='next') else None

    def run_crawler(self):
        """Main crawling loop."""
        # Implement crawling logic
        pass

    def check_and_fix_missing(self):
        """Handle missing chapters."""
        pass
```

Register in `main.py`:

```python
from crawlers.mynewsite import MyNewSiteCrawler

CRAWLER_REGISTRY = {
    "mynewsite.com": MyNewSiteCrawler,
    "www.mynewsite.com": MyNewSiteCrawler
}
```

## ⚙️ Configuration

Edit `config.py` to customize:
- Default output directory
- Retry attempts
- Timeout values
- API models
- Logging level
- And more!

## 🔐 API Key Setup

### Getting a Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key
4. Set environment variable:

```bash
# Linux/macOS
export GOOGLE_API_KEY="your_key_here"

# Windows (Command Prompt)
set GOOGLE_API_KEY=your_key_here

# Windows (PowerShell)
$env:GOOGLE_API_KEY="your_key_here"
```

Or enter interactively when prompted.

## 📖 Workflow

### Full Pipeline (Recommended)

```
Input URL → Crawl Chapters → Fix Missing → Enhance Text → Compile EPUB → Output
```

1. **Crawl** - Downloads chapters as CSV files
2. **Fix Missing** - Detects and recovers broken links
3. **Enhance** - Sends text to Gemini AI for translation fixes
4. **Compile** - Creates final EPUB file

### Step-by-Step

```bash
# Just crawl
Option [2]

# Enhance later
Option [4]

# Compile when ready
Option [5]
```

## 🧠 How AI Enhancement Works

1. Reads raw chapter text from CSV
2. Sends to Google Gemini API with instructions to:
   - Fix grammar and spelling
   - Improve awkward phrasing
   - Clarify untranslated terms
   - Maintain original meaning
3. Saves enhanced text back to CSV
4. Skips already-enhanced chapters

**Cost:** ~$0.01-0.05 per 100 chapters (Gemini free tier available)

## 📚 Output Format

### CSV Files
Each chapter is saved as `chapter_XXXX.csv`:
```
Title,Edited By,Chapter Body,Enhanced
"Ch 1: Beginning","Unknown","The story begins...","False"
```

### EPUB File
- Automatically named: `Novel_Title.epub`
- Readable on: Kindle, Apple Books, E-readers, Web browsers
- Includes: Table of Contents, proper formatting, styles

## 🐛 Troubleshooting

### "No chapters found"
- Check URL format
- Verify site is not blocked
- Try manual URL first

### "API key error"
- Verify key in environment: `echo $GOOGLE_API_KEY`
- Check key is valid at Google AI Studio
- Restart application

### "Enhanced: False" won't change to True
- Ensure Gemini API key is set
- Check internet connection
- Review novelforge.log for errors

### Windows path errors
- Use forward slashes or proper Python paths
- Don't manually edit CSV file paths

See `GITHUB_ACTIONS_TROUBLESHOOTING.md` for more issues.

## 💻 Requirements

```
Python 3.8+
beautifulsoup4==4.14.3
requests==2.32.5
google-genai==1.65.0
ebooklib==0.20
rich==14.3.3
```

See `requirements.txt` for complete list.

## 🔄 CI/CD Pipeline

Automated testing and building on every commit:

- **Testing** - Python 3.8-3.12, Windows/Linux/macOS
- **Linting** - Code style, type checking
- **Security** - Vulnerability scanning, secret detection
- **Release** - Automatic Windows EXE builds

See `.github/workflows/` for details.

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| `INSTALLATION_GUIDE.md` | Detailed setup instructions |
| `DEVELOPER_REFERENCE.md` | API reference & architecture |
| `GITHUB_ACTIONS_COMPLETE_GUIDE.md` | CI/CD setup & usage |
| `EPUB_ALTERNATIVES.md` | Compare EPUB libraries |
| `EPUB_MIGRATION_GUIDE.md` | Switch to pypub or Pandoc |

## 🤝 Contributing

Contributions welcome! To add a new crawler:

1. Create crawler class in `crawlers/`
2. Inherit from `BaseCrawler`
3. Implement `_parse_chapter()`, `_extract_next_link()`, `run_crawler()`, `check_and_fix_missing()`
4. Register in `main.py`
5. Test on 10+ chapters
6. Submit PR

See `CONTRIBUTION.md` for detailed guidelines.

## ⚠️ Disclaimer

This tool is for **personal, educational use only**. 

- Respect copyright of translators and original authors
- Comply with website Terms of Service
- Don't overload servers (built-in rate limiting included)
- Many web novels are fan translations - be respectful

## 📜 License

MIT License - See LICENSE file for details.

## 🙏 Credits

- Built with [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) for web scraping
- Enhanced with [Google Gemini API](https://aistudio.google.com/) for AI text improvement
- EPUB creation with [EbookLib](https://github.com/aerkalov/ebooklib)
- UI with [Rich](https://rich.readthedocs.io/)

## 📞 Support

- **Issues** - Open GitHub issue
- **Questions** - Check documentation first
- **Bugs** - Provide: OS, Python version, error log

## 🚀 Roadmap

- [ ] Async crawler variant for faster downloads
- [ ] Additional site crawlers (Wuxiaworld, Royal Road, etc.)
- [ ] Web dashboard interface
- [ ] Mobile app support
- [ ] Cloud deployment
- [ ] Advanced scheduling

## ✨ Version History

### v1.1.0 (Current)
- Production-ready infrastructure
- Enterprise-grade error handling
- GitHub Actions CI/CD
- 22 critical fixes
- Comprehensive documentation

### v1.0.0
- Initial release
- Basic crawling & compilation
- Single site support

## 💬 Feedback

Have suggestions? Found a bug? [Open an issue](https://github.com/yourusername/novelforge/issues)

---

**Made with ❤️ for light novel readers and developers**

*NovelForge: Where raw translations become refined stories.*