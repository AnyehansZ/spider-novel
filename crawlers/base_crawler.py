"""
NovelForge Base Crawler
Abstract base class for all site-specific crawlers.
Provides retry logic, error handling, and manifest tracking.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import logging

from error_handler import (
    retry_with_backoff,
    CrawlerError,
    ChapterNotFoundError,
    InvalidChapterDataError,
    ErrorContext,
    ErrorSummary,
)
from manifest_manager import ManifestManager, NovelManifest, ChapterRecord
import utils
import config as cfg

logger = logging.getLogger("NovelForge.BaseCrawler")


class BaseCrawler(ABC):
    """
    Abstract base class for all novel crawlers.
    
    Subclasses should implement:
    - _parse_chapter(soup): Extract title, editor, body from BeautifulSoup object
    - _extract_next_link(soup): Find the next chapter URL
    - run_crawler(): Main crawl loop
    - check_and_fix_missing(): Recover missing chapters
    """
    
    def __init__(
        self,
        novel_name: str,
        output_folder: Path,
        base_url: str,
        start_url: str,
    ):
        """
        Initialize the crawler.
        
        Args:
            novel_name: Display name of the novel
            output_folder: Path to save downloaded chapters
            base_url: Base URL of the website (e.g., https://example.com/novel/)
            start_url: Relative URL of first chapter
        """
        self.novel_name = novel_name
        self.output_folder = Path(output_folder)
        self.base_url = base_url
        self.start_url = start_url
        
        # Initialize utilities
        self.logger = logging.getLogger(f"NovelForge.{self.__class__.__name__}")
        self.manifest_manager = ManifestManager()
        
        # Initialize or load manifest
        self.novel_slug = self._slugify_name(novel_name)
        self.manifest: Optional[NovelManifest] = self._initialize_manifest()
        
        # Error tracking
        self.error_summary = ErrorSummary(f"Crawl: {novel_name}")
        
        self.logger.info(
            f"Initialized {self.__class__.__name__} for {novel_name} "
            f"at {base_url}"
        )
    
    def _slugify_name(self, name: str) -> str:
        """Convert name to slug for manifest filename."""
        from manifest_manager import slugify_novel_name
        return slugify_novel_name(name)
    
    def _initialize_manifest(self) -> NovelManifest:
        """Load existing manifest or create new one."""
        manifest = self.manifest_manager.load_manifest(self.novel_slug)
        
        if manifest:
            self.logger.info(f"Loaded existing manifest for {self.novel_name}")
            return manifest
        else:
            self.logger.info(f"Creating new manifest for {self.novel_name}")
            manifest = self.manifest_manager.create_manifest(
                self.novel_name,
                self.output_folder,
                self.novel_slug,
            )
            return manifest
    
    def save_manifest(self):
        """Save current manifest state to disk."""
        self.manifest_manager.save_manifest(self.manifest, self.novel_slug)
    
    # ====================================================================
    # ABSTRACT METHODS (must be implemented by subclasses)
    # ====================================================================
    
    @abstractmethod
    def _parse_chapter(self, soup) -> Tuple[str, str, str]:
        """
        Extract chapter data from parsed HTML.
        
        Args:
            soup: BeautifulSoup object of chapter page
        
        Returns:
            Tuple of (title, edited_by, body)
        
        Raises:
            InvalidChapterDataError if parsing fails
        """
        pass
    
    @abstractmethod
    def _extract_next_link(self, soup) -> Optional[str]:
        """
        Extract the next chapter URL from parsed HTML.
        
        Args:
            soup: BeautifulSoup object of chapter page
        
        Returns:
            Relative or absolute URL of next chapter, or None
        """
        pass
    
    @abstractmethod
    def run_crawler(self):
        """
        Main crawl loop. Should:
        1. Fetch chapters starting from start_url
        2. Save each chapter using save_chapter()
        3. Follow next chapter links
        4. Handle 404s and paywalls gracefully
        5. Update manifest state
        """
        pass
    
    @abstractmethod
    def check_and_fix_missing(self):
        """
        Detect and attempt to download missing chapters.
        Should:
        1. Identify gaps in chapter sequence
        2. Attempt to fetch missing chapters
        3. Update manifest with results
        4. Report unfixed chapters
        """
        pass
    
    # ====================================================================
    # HELPER METHODS
    # ====================================================================
    
    def save_chapter(
        self,
        chapter_num: int,
        title: str,
        edited_by: str,
        body: str,
        url: str = None,
    ) -> bool:
        """
        Save a chapter to CSV and update manifest.
        
        Args:
            chapter_num: Chapter number
            title: Chapter title
            edited_by: Editor name
            body: Chapter body text
            url: Source URL (optional, for manifest)
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Validate data
            from validators import validate_chapter_data
            chapter_num, title, edited_by, body = validate_chapter_data(
                chapter_num, title, edited_by, body
            )
            
            # Save to CSV
            success = utils.save_chapter_to_csv(
                self.output_folder,
                chapter_num,
                title,
                edited_by,
                body,
                enhanced="False",
                logger_obj=self.logger,
            )
            
            if success:
                # Update manifest
                record = ChapterRecord(chapter_num, title, "downloaded")
                record.url = url
                record.editor = edited_by
                self.manifest.add_chapter(record)
                self.manifest.mark_downloaded(chapter_num, url or "")
                self.save_manifest()
                
                self.error_summary.record_success()
                return True
            else:
                self.error_summary.add_error(chapter_num, Exception("CSV write failed"))
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to save chapter {chapter_num}: {str(e)}")
            self.error_summary.add_error(chapter_num, e)
            self.manifest.mark_error(chapter_num, str(e))
            self.save_manifest()
            return False
    
    def get_last_chapter_number(self) -> Optional[int]:
        """Get the last chapter number that was downloaded."""
        if self.manifest.chapters:
            return max(self.manifest.chapters.keys())
        return None
    
    def get_missing_chapters(self, max_chapter: int) -> list:
        """Get list of missing chapter numbers up to max."""
        return self.manifest.get_missing_chapters(max_chapter)
    
    def get_downloaded_count(self) -> int:
        """Get count of downloaded chapters."""
        downloaded = self.manifest.get_chapters_by_status("downloaded")
        return len(downloaded)
    
    def update_crawl_state(self, **kwargs):
        """Update crawl state in manifest."""
        self.manifest.update_crawl_state(**kwargs)
        self.save_manifest()
    
    def get_error_summary_str(self) -> str:
        """Get error summary as formatted string."""
        return self.error_summary.get_report()
    
    def save_error_report(self, output_path: Path = None):
        """Save error report to file."""
        if output_path is None:
            output_path = self.output_folder / "error_report.txt"
        
        self.error_summary.save_report(output_path)
    
    # ====================================================================
    # COMMON RETRY PATTERNS
    # ====================================================================
    
    def fetch_with_retry(
        self,
        url: str,
        max_retries: int = cfg.CRAWLER_MAX_RETRIES,
        timeout: int = cfg.CRAWLER_TIMEOUT,
    ):
        """
        Fetch a URL with automatic retry logic and exponential backoff.
        
        Args:
            url: URL to fetch
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        
        Returns:
            Response object or None if all retries fail
        """
        import requests
        
        @retry_with_backoff(
            max_attempts=max_retries,
            base_delay=1.0,
            backoff_factor=cfg.CRAWLER_RETRY_BACKOFF,
            exceptions=(requests.RequestException, TimeoutError),
            on_retry=lambda attempt, delay, exc: self.logger.warning(
                f"Retry {attempt}: {type(exc).__name__} - waiting {delay:.1f}s"
            ),
        )
        def _fetch():
            return requests.get(
                url,
                headers=self.get_headers(),
                timeout=timeout,
                allow_redirects=True,
            )
        
        try:
            return _fetch()
        except Exception as e:
            self.logger.error(f"Failed to fetch {url} after {max_retries} retries: {str(e)}")
            return None
    
    def get_headers(self) -> dict:
        """
        Get HTTP headers for requests.
        Override in subclass if custom headers needed.
        """
        return {
            "User-Agent": cfg.CRAWLER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }