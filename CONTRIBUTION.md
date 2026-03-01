### 2. `CONTRIBUTING.md`

```markdown
# Contributing to the Universal Novel Crawler

First off, thank you for considering contributing! The goal of this project is to build a robust, universal framework that can easily scrape, fix, and compile web novels from *any* website. 

The most common way to contribute is by **adding a crawler for a new website**.

## 🛠️ How to Add a New Site Crawler

Because the project is highly modular, the core logic (saving files, enhancing text, creating EPUBs) is entirely decoupled from the scraping logic. 

To add a new site, you only need to create one file inside the `crawlers/` directory.

### Step 1: Create a new file
Create a new file in the `crawlers/` folder named after the website (e.g., `crawlers/wuxiaworld.py`).

### Step 2: Inherit from `BaseCrawler`
Your new class must inherit from `BaseCrawler` and implement the `run_crawler()` and `check_and_fix_missing()` methods. 

Here is a minimal template:

```python
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from crawlers.base_crawler import BaseCrawler
import utils

class NewSiteCrawler(BaseCrawler):
    def __init__(self, output_folder="novels/my_new_novel"):
        super().__init__("My New Novel Title", output_folder)
        self.base_url = "https://example-novel-site.com/"
        self.start_url = "chapter-1"
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def _parse_chapter(self, soup):
        """Locate HTML elements specific to this website."""
        # TODO: Find Title
        title = soup.find('h1', class_='chapter-title').text
        
        # TODO: Find Editor/Author
        edited_by = "Unknown"
        
        # TODO: Find Body Text
        paragraphs = soup.find('div', class_='chapter-content').find_all('p')
        body = "\n".join([p.text for p in paragraphs])
        
        return title, edited_by, body

    def _extract_next_link(self, soup):
        """Find the 'Next Chapter' button href."""
        next_btn = soup.find('a', class_='next-button')
        return next_btn.get('href') if next_btn else None

    def run_crawler(self):
        """Implement your traversal loop here using utils.save_chapter_to_csv()"""
        # See crawlers/xiaxuenovels.py for a complete loop example!
        pass

    def check_and_fix_missing(self):
        """Implement custom missing-chapter URL bypass logic for this specific site."""
        pass
```

### Step 3: Register your crawler in `main.py`
Open `main.py` and import your new crawler. Update the CLI logic to allow users to select your crawler (e.g., adding a prompt to select which website to target before showing the main menu).

---

## 🧠 Improving Core Modules

### Enhancer (`enhancer.py`)
If you want to tweak the Gemini AI prompts to yield better translation fixes, or if you want to add support for alternative LLMs (like OpenAI or Anthropic), modify the `EnhanceAPI` class. Ensure that the `process_text(text)` function signature remains unchanged so it doesn't break `main.py`.

### Compiler (`compiler.py`)
If you want to improve the CSS styling of the outputted EPUB, add cover images, or tweak the EbookLib generation, modify the `compile_epub()` function.

## 📜 Pull Request Guidelines
1. Fork the repo and create your branch from `main`.
2. Ensure you respect rate limits (use `time.sleep()`) in your crawlers to prevent server abuse.
3. Test your crawler on at least 10 chapters to ensure formatting remains stable.
4. Open a Pull Request!
```