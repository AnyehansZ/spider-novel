```markdown
# Universal Light Novel Crawler & AI Enhancer 📚✨

An automated, modular framework designed to scrape web novels, fix poorly machine-translated (MTL) text using the Google Gemini AI, and compile the polished chapters into beautifully formatted EPUB eBooks.

## ✨ Features
* **Modular Crawler System**: Easily expandable to support any light novel website.
* **AI Translation Enhancement**: Uses the `google-genai` SDK to naturally rewrite and fix bad grammar, untranslated terms, and awkward phrasing while preserving the original meaning.
* **Smart Recovery & Paywall Bypass**: Automatically detects missing links, 404s, or Patreon paywalls and attempts URL manipulation to fetch missing chapters.
* **Resumable Operations**: Downloads and enhancements are saved in standard CSV formats. You can pause and resume crawling or AI processing at any time.
* **One-Click EPUB Compilation**: Automatically sorts chapters numerically and builds a styled EPUB file with a generated Table of Contents.

## 📂 Project Structure
```text
├── main.py                  # The central CLI application
├── utils.py                 # Helper functions (CSV handling, regex, file sorting)
├── enhancer.py              # Gemini AI logic for text enhancement
├── compiler.py              # Ebooklib logic for EPUB generation
├── crawlers/                # Folder containing site-specific scrapers
│   ├── base_crawler.py      # The blueprint class for all crawlers
│   └── xiaxuenovels.py      # Example scraper for XiaXue Novels
└── novels/                  # Output directory where CSVs and EPUBs are saved
```

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/novel-crawler-enhancer.git
   cd novel-crawler-enhancer
   ```

2. **Install required dependencies:**
   Make sure you have Python 3.8+ installed.
   ```bash
   pip install requests beautifulsoup4 ebooklib google-genai
   ```

3. **Set your Google Gemini API Key:**
   The Enhancer module requires a valid Google Gemini API key. Get one from Google AI Studio and set it in your environment variables:
   
   *Windows (Command Prompt):*
   ```cmd
   set GOOGLE_API_KEY=your_api_key_here
   ```
   *Mac/Linux:*
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   ```

## 🚀 Usage

Run the central manager:
```bash
python main.py
```

You will be presented with a menu:
1. **Run Full Auto-Pipeline**: Crawls the site, checks for missing chapters, runs the AI enhancer, and outputs an EPUB.
2. **Start / Resume Crawling**: Scrapes the targeted website and saves chapters as individual CSVs.
3. **Check and Fix Missing Chapters**: Scans your downloaded CSVs, identifies gaps, and attempts to bypass broken links to download missing content.
4. **Enhance Downloaded CSVs**: Sends raw chapter text to Gemini for editing. Skips already-enhanced chapters.
5. **Compile CSVs to EPUB**: Combines all downloaded/enhanced chapters into a finalized eBook.

## ⚠️ Disclaimer
This tool is for personal, educational use only. Please respect the copyright of translators and original authors. Ensure you comply with the Terms of Service of the websites you scrape and do not overload their servers (the crawler includes built-in rate-limiting delays to be respectful).
```