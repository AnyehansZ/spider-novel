import time
import random
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from rich.console import Console

from crawlers.base_crawler import BaseCrawler
from utils import logger
import utils

console = Console()

class XiaXueCrawler(BaseCrawler):
    def __init__(self, novel_name, output_folder, base_url, start_url):
        super().__init__(novel_name, output_folder, base_url, start_url)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        # Dynamically deduce chapter prefix for URL manipulation bypass
        # Example: 'btc-chapter-1' -> prefix becomes 'btc-chapter-'
        match = re.search(r'(.*?)-?\d+/?$', self.start_url)
        if match:
            extracted_prefix = match.group(1)
            self.chapter_prefix = extracted_prefix + "-" if not extracted_prefix.endswith('-') else extracted_prefix
        else:
            self.chapter_prefix = "chapter-" # Fallback

    def _extract_number_from_url(self, url):
        match = re.search(r'chapter-(\d+)', url)
        return int(match.group(1)) if match else None

    def _parse_chapter(self, soup):
        # 1. Title
        title = "Unknown Chapter"
        trail_item = soup.find('li', class_='trail-item trail-end')
        if trail_item:
            title_span = trail_item.find('span', attrs={'itemprop': 'name'})
            if title_span: title = title_span.get_text(strip=True)
        if title == "Unknown Chapter":
            nav_title = soup.find('li', class_='post-nav-title')
            if nav_title: title = nav_title.get_text(strip=True)

        # 2. Editor
        edited_by = "Unknown"
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text.startswith('Edited:'):
                edited_by = text.replace('Edited:', '').strip()
                break

        # 3. Body
        body_content = []
        spans = soup.find_all('span', class_='notranslate')
        if spans:
            body_content = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]
        else:
            content_area = soup.find('div', class_='post-content') or soup.find('div', class_='entry-content')
            paragraphs = content_area.find_all('p') if content_area else soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if not text or text.startswith('[') or text.startswith('Edited:') or 'adsbygoogle' in text:
                    continue
                body_content.append(text)

        return title, edited_by, "\n".join(body_content)

    def _extract_next_link(self, soup):
        wp_post_nav = soup.find('nav', class_='wp-post-nav')
        if wp_post_nav:
            next_links = wp_post_nav.find_all('a', rel='next')
            if next_links: return next_links[0].get('href')

        nav_next = soup.find('div', class_='nav-next')
        if nav_next:
            a_tag = nav_next.find('a', rel='next')
            if a_tag: return a_tag.get('href')

        paragraphs = soup.find_all('p', style='text-align: center;')
        for p in paragraphs:
            links = p.find_all('a')
            if links and 'Next' in links[-1].text:
                return links[-1].get('href')
                
        return None

    def _fetch_and_save(self, url, expected_num=None):
        try:
            time.sleep(random.uniform(1, 3))
            logger.info(f"Fetching URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 404:
                logger.warning(f"404 Not Found at {url}")
                return None, None

            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, "html.parser")
            
            chapter_num = self._extract_number_from_url(url) or expected_num
            title, edited_by, body = self._parse_chapter(soup)
            
            if not body.strip():
                logger.error(f"No content found for chapter {chapter_num}")
                return chapter_num, None
            
            utils.save_chapter_to_csv(self.output_folder, chapter_num, title, edited_by, body)
            return chapter_num, self._extract_next_link(soup)

        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return expected_num, None

    def run_crawler(self):
        downloaded = utils.get_downloaded_chapters(self.output_folder)
        
        if downloaded:
            last_chap = downloaded[-1]
            current_url = urljoin(self.base_url, f"{self.chapter_prefix}{last_chap + 1}")
            logger.info(f"Resuming from chapter {last_chap + 1}")
        else:
            current_url = urljoin(self.base_url, self.start_url)
            logger.info("Starting fresh crawl")

        consecutive_fails = 0

        # --- RICH SPINNER UI ---
        with console.status("[bold green]Crawling chapters...", spinner="dots") as status:
            while current_url and consecutive_fails < 3:
                # Update spinner text dynamically
                status.update(f"[bold green]Crawling:[/bold green] {current_url}")
                
                chap_num, next_link = self._fetch_and_save(current_url)
                if not chap_num: break

                if next_link and 'patreon.com' in next_link.lower():
                    logger.info("Patreon paywall detected. Bypassing...")
                    current_url = urljoin(self.base_url, f"{self.chapter_prefix}{chap_num + 1}")
                    consecutive_fails = 0
                elif next_link:
                    current_url = urljoin(current_url, next_link)
                    consecutive_fails = 0
                else:
                    logger.warning("No next link found. Attempting dynamic bypass...")
                    current_url = urljoin(self.base_url, f"{self.chapter_prefix}{chap_num + 1}")
                    consecutive_fails += 1

        console.print("[bold green]✅ Crawling phase complete![/bold green]")

    def check_and_fix_missing(self):
        console.print("[bold cyan]\n--- Checking for Missing Chapters ---[/bold cyan]")
        downloaded = utils.get_downloaded_chapters(self.output_folder)
        
        if not downloaded:
            console.print("[yellow]No chapters downloaded yet. Run the crawler first.[/yellow]")
            return
            
        max_chap = downloaded[-1]
        missing = [i for i in range(1, max_chap + 1) if i not in downloaded]

        if not missing:
            console.print("[bold green]✅ All chapters present! No missing files.[/bold green]")
            return
            
        console.print(f"[bold yellow]⚠️ Found {len(missing)} missing chapters:[/bold yellow] {missing}")
        logger.info(f"Attempting to download {len(missing)} missing chapters: {missing}")
        
        with console.status("[bold yellow]Fixing missing chapters...", spinner="bouncingBar") as status:
            for chap_num in missing:
                status.update(f"[bold yellow]Fetching missing chapter {chap_num}...[/bold yellow]")
                url = urljoin(self.base_url, f"{self.chapter_prefix}{chap_num}")
                self._fetch_and_save(url, expected_num=chap_num)
                
        # Final Verification
        downloaded = utils.get_downloaded_chapters(self.output_folder)
        missing_after = [i for i in range(1, max_chap + 1) if i not in downloaded]
        
        if not missing_after:
            console.print("[bold green]✅ Successfully recovered all missing chapters![/bold green]")
            logger.info("Successfully recovered all missing chapters.")
        else:
            console.print(f"[bold red]❌ Still missing chapters:[/bold red] {missing_after}")
            logger.error(f"Failed to recover chapters: {missing_after}")