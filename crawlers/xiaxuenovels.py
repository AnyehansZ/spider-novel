"""
NovelForge XiaXue Novels Crawler
Crawler implementation for xiaxuenovels.xyz
Features: Retry logic, paywall detection, chapter recovery, manifest tracking
"""

import time
import random
import re
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from base_crawler import BaseCrawler
from error_handler import (
    retry_with_backoff,
    ChapterNotFoundError,
    InvalidChapterDataError,
    PaywallError,
    NetworkError,
)
import config as cfg
import validators

logger = logging.getLogger("NovelForge.XiaXueCrawler")


class XiaXueCrawler(BaseCrawler):
    """
    Crawler for xiaxuenovels.xyz
    Handles paywall detection, chapter URL reconstruction, and recovery.
    """
    
    def __init__(
        self,
        novel_name: str,
        output_folder: Path,
        base_url: str,
        start_url: str,
    ):
        """
        Initialize crawler for XiaXue Novels.
        
        Args:
            novel_name: Novel name
            output_folder: Output folder path
            base_url: Base URL (e.g., https://xiaxuenovels.xyz/my-novel/)
            start_url: Start chapter URL slug
        """
        super().__init__(novel_name, output_folder, base_url, start_url)
        
        # Deduce chapter prefix for URL reconstruction
        # e.g., "chapter-1" -> "chapter-"
        self.chapter_prefix = self._deduce_chapter_prefix(start_url)
        
        logger.info(f"Deduced chapter prefix: {self.chapter_prefix}")
    
    def _deduce_chapter_prefix(self, start_url: str) -> str:
        """
        Extract chapter prefix from start URL.
        e.g., "mr-chapter-1" -> "mr-chapter-"
        e.g., "chapter-1" -> "chapter-"
        """
        match = re.search(r'(.*?)-?\d+/?$', start_url)
        if match:
            prefix = match.group(1)
            return prefix + "-" if not prefix.endswith('-') else prefix
        
        logger.warning(f"Could not deduce prefix from {start_url}, using default")
        return "chapter-"
    
    def _extract_number_from_url(self, url: str) -> Optional[int]:
        """Extract chapter number from URL."""
        match = re.search(r'chapter-(\d+)', url)
        return int(match.group(1)) if match else None
    
    def _parse_chapter(self, soup: BeautifulSoup) -> tuple:
        """
        Extract chapter data from HTML.
        Supports multiple HTML structure variants.
        
        Returns:
            Tuple of (title, edited_by, body)
        
        Raises:
            InvalidChapterDataError if parsing fails
        """
        try:
            # Method 1: Breadcrumb trail
            title = "Unknown Chapter"
            trail_item = soup.find('li', class_='trail-item trail-end')
            if trail_item:
                title_span = trail_item.find('span', attrs={'itemprop': 'name'})
                if title_span:
                    title = title_span.get_text(strip=True)
            
            # Method 2: Post nav title
            if title == "Unknown Chapter":
                nav_title = soup.find('li', class_='post-nav-title')
                if nav_title:
                    title = nav_title.get_text(strip=True)
            
            # Extract editor
            edited_by = "Unknown"
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text.startswith('Edited:') or text.startswith('Editor:'):
                    edited_by = re.sub(r'^(Edited|Editor):\s*', '', text).strip()
                    break
            
            # Extract body content (try multiple methods)
            body_parts = []
            
            # Method 1: notranslate spans
            spans = soup.find_all('span', class_='notranslate')
            if spans:
                body_parts = [
                    s.get_text(strip=True)
                    for s in spans
                    if s.get_text(strip=True)
                ]
            
            # Method 2: post-content or entry-content divs
            if not body_parts:
                content_div = (
                    soup.find('div', class_='post-content')
                    or soup.find('div', class_='entry-content')
                    or soup.find('article')
                )
                
                if content_div:
                    for p in content_div.find_all('p'):
                        text = p.get_text(strip=True)
                        
                        # Skip non-content paragraphs
                        if (text and 
                            not text.startswith('[') and 
                            not text.startswith('Edited:') and
                            'adsbygoogle' not in text):
                            body_parts.append(text)
            
            # Validate results
            if not body_parts or not body_parts[0]:
                raise InvalidChapterDataError(
                    f"No body content found for chapter: {title}"
                )
            
            body = "\n".join(body_parts)
            
            logger.debug(f"Parsed: {title} ({len(body)} chars)")
            return title, edited_by, body
        
        except Exception as e:
            raise InvalidChapterDataError(f"Failed to parse chapter: {str(e)}")
    
    def _extract_next_link(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract next chapter link from multiple possible locations.
        
        Returns:
            Next chapter URL or None
        """
        # Method 1: wp-post-nav
        wp_post_nav = soup.find('nav', class_='wp-post-nav')
        if wp_post_nav:
            next_links = wp_post_nav.find_all('a', rel='next')
            if next_links:
                return next_links[0].get('href')
        
        # Method 2: nav-next div
        nav_next = soup.find('div', class_='nav-next')
        if nav_next:
            a_tag = nav_next.find('a', rel='next')
            if a_tag:
                return a_tag.get('href')
        
        # Method 3: Center-aligned paragraphs with links
        paragraphs = soup.find_all('p', style='text-align: center;')
        for p in paragraphs:
            links = p.find_all('a')
            if links:
                for link in links:
                    if 'next' in link.text.lower():
                        return link.get('href')
        
        return None
    
    def _is_paywall(self, url: str, response_text: str) -> bool:
        """Detect if response contains paywall message."""
        paywall_indicators = [
            'patreon',
            'exclusive',
            'members only',
            'login required',
            'subscribe',
            'premium',
        ]
        
        text_lower = response_text.lower()
        return any(indicator in text_lower for indicator in paywall_indicators)
    
    @retry_with_backoff(
        max_attempts=cfg.CRAWLER_MAX_RETRIES,
        base_delay=1.0,
        backoff_factor=cfg.CRAWLER_RETRY_BACKOFF,
        exceptions=(requests.RequestException, NetworkError),
    )
    def _fetch_chapter(self, url: str, timeout: int = cfg.CRAWLER_TIMEOUT):
        """
        Fetch chapter from URL with retry logic.
        
        Args:
            url: Chapter URL
            timeout: Request timeout in seconds
        
        Returns:
            Response object
        
        Raises:
            ChapterNotFoundError: If 404
            PaywallError: If paywall detected
            NetworkError: On network failures
        """
        try:
            response = self.fetch_with_retry(url, timeout=timeout)
            
            if response is None:
                raise NetworkError(f"Failed to fetch {url}")
            
            if response.status_code == 404:
                raise ChapterNotFoundError(f"Chapter not found: {url}")
            
            if response.status_code == 403:
                raise PaywallError(f"Access forbidden (paywall): {url}")
            
            if response.status_code != 200:
                raise NetworkError(
                    f"HTTP {response.status_code} from {url}"
                )
            
            # Check for paywall in content
            if self._is_paywall(url, response.text):
                raise PaywallError(f"Paywall detected for {url}")
            
            response.encoding = 'utf-8'
            return response
        
        except requests.Timeout:
            raise NetworkError(f"Timeout fetching {url}")
        except requests.RequestException as e:
            raise NetworkError(f"Request failed for {url}: {str(e)}")
    
    def _fetch_and_save_chapter(
        self,
        url: str,
        expected_num: Optional[int] = None,
    ) -> Optional[tuple]:
        """
        Fetch chapter from URL and save to CSV.
        
        Args:
            url: Chapter URL
            expected_num: Expected chapter number (for recovery)
        
        Returns:
            Tuple of (chapter_num, next_url) or (None, None) if failed
        """
        try:
            # Fetch page
            logger.info(f"Fetching: {url}")
            response = self._fetch_chapter(url)
            
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract chapter data
            try:
                title, edited_by, body = self._parse_chapter(soup)
            except InvalidChapterDataError as e:
                logger.error(f"Parsing error: {str(e)}")
                self.error_summary.add_error(
                    expected_num or "unknown",
                    e,
                    str(e),
                )
                return None, None
            
            # Determine chapter number
            chapter_num = self._extract_number_from_url(url) or expected_num
            if chapter_num is None:
                logger.warning(f"Could not determine chapter number from {url}")
                return None, None
            
            # Save to CSV
            if self.save_chapter(chapter_num, title, edited_by, body, url):
                self.update_crawl_state(
                    last_url=url,
                    last_chapter=chapter_num,
                    consecutive_failures=0,
                )
                
                # Get next link
                next_link = self._extract_next_link(soup)
                return chapter_num, next_link
            else:
                return chapter_num, None
        
        except PaywallError as e:
            logger.warning(f"Paywall: {str(e)}")
            return expected_num, None
        
        except ChapterNotFoundError as e:
            logger.warning(f"Not found: {str(e)}")
            return expected_num, None
        
        except NetworkError as e:
            logger.error(f"Network error: {str(e)}")
            self.error_summary.add_error(expected_num or "unknown", e)
            return expected_num, None
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self.error_summary.add_error(expected_num or "unknown", e)
            return expected_num, None
    
    def run_crawler(self):
        """
        Main crawl loop.
        Resumes from last chapter or starts fresh.
        """
        # Determine starting point
        last_chapter = self.get_last_chapter_number()
        
        if last_chapter:
            logger.info(f"Resuming from chapter {last_chapter + 1}")
            current_url = urljoin(
                self.base_url,
                f"{self.chapter_prefix}{last_chapter + 1}",
            )
        else:
            logger.info("Starting fresh crawl")
            current_url = urljoin(self.base_url, self.start_url)
        
        self.update_crawl_state(started_at=None, status="crawling")
        
        consecutive_fails = 0
        max_fails = cfg.CRAWLER_CONSECUTIVE_FAILS_LIMIT
        
        # Main crawl loop
        while current_url and consecutive_fails < max_fails:
            # Add random delay to be respectful
            delay = random.uniform(
                cfg.CRAWLER_DELAY_MIN,
                cfg.CRAWLER_DELAY_MAX,
            )
            time.sleep(delay)
            
            # Fetch and save chapter
            chapter_num, next_link = self._fetch_and_save_chapter(current_url)
            
            if chapter_num is None:
                consecutive_fails += 1
                self.update_crawl_state(
                    consecutive_failures=consecutive_fails
                )
                
                if consecutive_fails >= max_fails:
                    logger.info(
                        f"Stopping after {consecutive_fails} consecutive failures"
                    )
                    break
                
                continue
            
            consecutive_fails = 0
            
            # Determine next URL
            if next_link:
                # Check for paywall in next link
                if 'patreon.com' in next_link.lower():
                    logger.info("Patreon paywall detected, bypassing...")
                    current_url = urljoin(
                        self.base_url,
                        f"{self.chapter_prefix}{chapter_num + 1}",
                    )
                else:
                    current_url = urljoin(current_url, next_link)
            else:
                # Try to construct next chapter URL
                logger.debug("No next link found, constructing URL...")
                current_url = urljoin(
                    self.base_url,
                    f"{self.chapter_prefix}{chapter_num + 1}",
                )
        
        self.update_crawl_state(status="idle")
        logger.info(self.error_summary.get_report())
    
    def check_and_fix_missing(self):
        """
        Detect and recover missing chapters.
        """
        logger.info("Checking for missing chapters...")
        
        last_chapter = self.get_last_chapter_number()
        if not last_chapter:
            logger.warning("No chapters downloaded yet")
            return
        
        missing = self.get_missing_chapters(last_chapter)
        
        if not missing:
            logger.info("✓ All chapters present")
            return
        
        logger.warning(f"Found {len(missing)} missing chapters: {missing}")
        
        # Attempt to recover missing chapters
        for chapter_num in missing:
            url = urljoin(
                self.base_url,
                f"{self.chapter_prefix}{chapter_num}",
            )
            
            logger.info(f"Attempting to recover chapter {chapter_num}...")
            self._fetch_and_save_chapter(url, chapter_num)
            
            # Rate limiting
            time.sleep(random.uniform(
                cfg.CRAWLER_DELAY_MIN,
                cfg.CRAWLER_DELAY_MAX,
            ))
        
        # Final verification
        missing_after = self.get_missing_chapters(last_chapter)
        
        if missing_after:
            logger.warning(f"Still missing: {missing_after}")
        else:
            logger.info("✓ All missing chapters recovered!")
        
        logger.info(self.error_summary.get_report())