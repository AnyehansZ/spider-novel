"""
NovelForge Manifest Manager
Persistent state tracking for crawlers, enhancements, and compilations.
Allows resuming interrupted operations and tracking progress.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

from error_handler import ValidationError, ErrorContext
import config as cfg
import validators

logger = logging.getLogger("NovelForge.ManifestManager")


# ============================================================================
# MANIFEST DATA STRUCTURES
# ============================================================================

class ChapterRecord:
    """Record of a single chapter's status."""
    
    def __init__(self, chapter_num: int, title: str = "", status: str = "pending"):
        """
        Args:
            chapter_num: Chapter number
            title: Chapter title
            status: One of: pending, downloaded, enhanced, compiled
        """
        self.chapter_num = chapter_num
        self.title = title
        self.status = status
        self.url = None
        self.editor = ""
        self.content_hash = None
        self.downloaded_at = None
        self.enhanced_at = None
        self.error_count = 0
        self.last_error = None
    
    def to_dict(self) -> dict:
        return {
            "chapter_num": self.chapter_num,
            "title": self.title,
            "status": self.status,
            "url": self.url,
            "editor": self.editor,
            "content_hash": self.content_hash,
            "downloaded_at": self.downloaded_at,
            "enhanced_at": self.enhanced_at,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "ChapterRecord":
        record = ChapterRecord(data["chapter_num"], data.get("title", ""))
        record.status = data.get("status", "pending")
        record.url = data.get("url")
        record.editor = data.get("editor", "")
        record.content_hash = data.get("content_hash")
        record.downloaded_at = data.get("downloaded_at")
        record.enhanced_at = data.get("enhanced_at")
        record.error_count = data.get("error_count", 0)
        record.last_error = data.get("last_error")
        return record


class NovelManifest:
    """Complete manifest for a novel's crawl/enhancement state."""
    
    MANIFEST_VERSION = 2
    
    def __init__(self, novel_name: str, output_folder: Path):
        """
        Args:
            novel_name: Name of the novel
            output_folder: Path to the novel's output folder
        """
        self.version = self.MANIFEST_VERSION
        self.novel_name = novel_name
        self.output_folder = Path(output_folder)
        
        # State tracking
        self.chapters: Dict[int, ChapterRecord] = {}
        self.crawl_state = {
            "started_at": None,
            "last_url": None,
            "last_chapter": None,
            "status": "idle",  # idle, crawling, paused, error
            "consecutive_failures": 0,
        }
        
        self.enhancement_state = {
            "started_at": None,
            "last_enhanced_chapter": None,
            "status": "idle",  # idle, enhancing, paused, error
            "total_enhanced": 0,
        }
        
        self.compilation_state = {
            "last_compiled_at": None,
            "last_compiled_file": None,
            "chapter_count": 0,
        }
        
        self.created_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()
    
    def add_chapter(self, chapter_record: ChapterRecord):
        """Add or update a chapter record."""
        self.chapters[chapter_record.chapter_num] = chapter_record
        self._mark_updated()
    
    def get_chapter(self, chapter_num: int) -> Optional[ChapterRecord]:
        """Get a chapter record by number."""
        return self.chapters.get(chapter_num)
    
    def get_missing_chapters(self, max_chapter: int) -> List[int]:
        """Get list of chapters that should exist but don't."""
        existing = set(self.chapters.keys())
        all_chapters = set(range(1, max_chapter + 1))
        return sorted(all_chapters - existing)
    
    def get_chapters_by_status(self, status: str) -> List[ChapterRecord]:
        """Get all chapters with a specific status."""
        return [r for r in self.chapters.values() if r.status == status]
    
    def mark_downloaded(self, chapter_num: int, url: str, content_hash: str = None):
        """Mark a chapter as downloaded."""
        record = self.get_chapter(chapter_num)
        if record:
            record.status = "downloaded"
            record.downloaded_at = datetime.now().isoformat()
            record.url = url
            record.content_hash = content_hash
            record.error_count = 0
            record.last_error = None
            self._mark_updated()
    
    def mark_enhanced(self, chapter_num: int):
        """Mark a chapter as enhanced."""
        record = self.get_chapter(chapter_num)
        if record:
            record.status = "enhanced"
            record.enhanced_at = datetime.now().isoformat()
            self.enhancement_state["total_enhanced"] += 1
            self._mark_updated()
    
    def mark_error(self, chapter_num: int, error_message: str):
        """Record an error for a chapter."""
        record = self.get_chapter(chapter_num)
        if record:
            record.error_count += 1
            record.last_error = error_message
            self._mark_updated()
    
    def update_crawl_state(self, **kwargs):
        """Update crawl state."""
        for key, value in kwargs.items():
            if key in self.crawl_state:
                self.crawl_state[key] = value
        self._mark_updated()
    
    def update_enhancement_state(self, **kwargs):
        """Update enhancement state."""
        for key, value in kwargs.items():
            if key in self.enhancement_state:
                self.enhancement_state[key] = value
        self._mark_updated()
    
    def to_dict(self) -> dict:
        """Convert manifest to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "novel_name": self.novel_name,
            "output_folder": str(self.output_folder),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "chapters": {
                str(num): record.to_dict()
                for num, record in self.chapters.items()
            },
            "crawl_state": self.crawl_state,
            "enhancement_state": self.enhancement_state,
            "compilation_state": self.compilation_state,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "NovelManifest":
        """Create manifest from dictionary (JSON deserialization)."""
        manifest = NovelManifest(
            data["novel_name"],
            data["output_folder"]
        )
        manifest.version = data.get("version", 1)
        manifest.created_at = data.get("created_at", "")
        manifest.last_updated = data.get("last_updated", "")
        
        # Restore chapters
        for chapter_num_str, chapter_data in data.get("chapters", {}).items():
            record = ChapterRecord.from_dict(chapter_data)
            manifest.chapters[record.chapter_num] = record
        
        manifest.crawl_state = data.get("crawl_state", manifest.crawl_state)
        manifest.enhancement_state = data.get("enhancement_state", manifest.enhancement_state)
        manifest.compilation_state = data.get("compilation_state", manifest.compilation_state)
        
        return manifest
    
    def _mark_updated(self):
        """Mark the manifest as updated."""
        self.last_updated = datetime.now().isoformat()


# ============================================================================
# MANIFEST MANAGER
# ============================================================================

class ManifestManager:
    """Manage manifest persistence and operations."""
    
    def __init__(self, novels_dir: Path = None):
        """
        Args:
            novels_dir: Base directory for all novels (defaults to config)
        """
        self.novels_dir = Path(novels_dir or cfg.NOVELS_DIR)
        self.manifest_dir = self.novels_dir / ".manifest"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ManifestManager initialized at {self.manifest_dir}")
    
    def _get_manifest_path(self, novel_slug: str) -> Path:
        """Get the manifest file path for a novel."""
        return self.manifest_dir / f"{novel_slug}.manifest.json"
    
    def load_manifest(self, novel_slug: str) -> Optional[NovelManifest]:
        """
        Load an existing manifest from disk.
        
        Args:
            novel_slug: Slugified novel name
        
        Returns:
            NovelManifest or None if doesn't exist
        """
        manifest_path = self._get_manifest_path(novel_slug)
        
        if not manifest_path.exists():
            logger.debug(f"Manifest not found for {novel_slug}")
            return None
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            manifest = NovelManifest.from_dict(data)
            logger.info(f"Loaded manifest for {manifest.novel_name}")
            return manifest
        
        except Exception as e:
            logger.error(f"Failed to load manifest {manifest_path}: {str(e)}")
            return None
    
    def save_manifest(self, manifest: NovelManifest, novel_slug: str):
        """
        Save a manifest to disk.
        
        Args:
            manifest: NovelManifest object
            novel_slug: Slugified novel name
        """
        manifest_path = self._get_manifest_path(novel_slug)
        
        try:
            # Create backup of previous manifest
            if manifest_path.exists():
                backup_path = manifest_path.with_suffix('.json.bak')
                manifest_path.rename(backup_path)
                logger.debug(f"Created backup: {backup_path}")
            
            # Write new manifest
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved manifest for {manifest.novel_name}")
        
        except Exception as e:
            logger.error(f"Failed to save manifest {manifest_path}: {str(e)}")
            raise
    
    def create_manifest(
        self,
        novel_name: str,
        output_folder: Path,
        novel_slug: str,
    ) -> NovelManifest:
        """
        Create a new manifest and save it.
        
        Args:
            novel_name: Full novel name
            output_folder: Path to output folder
            novel_slug: Slugified novel name for manifest filename
        
        Returns:
            Created NovelManifest
        """
        manifest = NovelManifest(novel_name, output_folder)
        self.save_manifest(manifest, novel_slug)
        return manifest
    
    def delete_manifest(self, novel_slug: str) -> bool:
        """
        Delete a manifest file.
        
        Args:
            novel_slug: Slugified novel name
        
        Returns:
            True if deleted, False if not found
        """
        manifest_path = self._get_manifest_path(novel_slug)
        
        if manifest_path.exists():
            try:
                manifest_path.unlink()
                logger.info(f"Deleted manifest for {novel_slug}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete manifest {manifest_path}: {str(e)}")
                return False
        
        return False
    
    def get_all_manifests(self) -> Dict[str, NovelManifest]:
        """
        Load all manifests from disk.
        
        Returns:
            Dictionary mapping novel_slug -> NovelManifest
        """
        manifests = {}
        
        for manifest_path in self.manifest_dir.glob("*.manifest.json"):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                manifest = NovelManifest.from_dict(data)
                slug = manifest_path.stem.replace('.manifest', '')
                manifests[slug] = manifest
            
            except Exception as e:
                logger.warning(f"Failed to load {manifest_path}: {str(e)}")
        
        return manifests
    
    def get_last_crawl_url(self, novel_slug: str) -> Optional[str]:
        """Get the last URL that was crawled."""
        manifest = self.load_manifest(novel_slug)
        if manifest:
            return manifest.crawl_state.get("last_url")
        return None
    
    def get_last_chapter_number(self, novel_slug: str) -> Optional[int]:
        """Get the last chapter number that was downloaded."""
        manifest = self.load_manifest(novel_slug)
        if manifest:
            if manifest.chapters:
                return max(manifest.chapters.keys())
        return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def slugify_novel_name(novel_name: str) -> str:
    """Convert novel name to slug for use in filenames/URLs."""
    slug = novel_name.lower()
    slug = slug.replace(' ', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    slug = slug.strip('-')
    return slug or 'unknown'


def generate_manifest_report(manifest: NovelManifest) -> str:
    """Generate a human-readable report from a manifest."""
    lines = [
        f"\n{'='*60}",
        f"Novel: {manifest.novel_name}",
        f"Created: {manifest.created_at}",
        f"Updated: {manifest.last_updated}",
        f"{'='*60}",
        f"\nChapters: {len(manifest.chapters)}",
    ]
    
    # Chapter status breakdown
    status_counts = {}
    for record in manifest.chapters.values():
        status = record.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        lines.append(f"  • {status.capitalize()}: {count}")
    
    # Crawl state
    lines.append(f"\nCrawl Status: {manifest.crawl_state['status']}")
    lines.append(f"  Last URL: {manifest.crawl_state['last_url']}")
    lines.append(f"  Failures: {manifest.crawl_state['consecutive_failures']}")
    
    # Enhancement state
    lines.append(f"\nEnhancement Status: {manifest.enhancement_state['status']}")
    lines.append(f"  Total Enhanced: {manifest.enhancement_state['total_enhanced']}")
    
    # Compilation state
    lines.append(f"\nCompilation Status:")
    lines.append(f"  Last Compiled: {manifest.compilation_state['last_compiled_at']}")
    lines.append(f"  Chapters in EPUB: {manifest.compilation_state['chapter_count']}")
    
    lines.append(f"\n{'='*60}\n")
    return "\n".join(lines)