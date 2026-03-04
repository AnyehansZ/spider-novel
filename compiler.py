"""
NovelForge EPUB Compiler
Converts CSV chapters into beautifully formatted EPUB eBooks.
Features: validation, error handling, progress tracking, metadata support.
"""

import logging
from pathlib import Path
from typing import Optional, List
from ebooklib import epub
import csv
import io

from error_handler import CompilerError, ErrorSummary, SafeFileOperation
from manifest_manager import ManifestManager
import utils
import config as cfg
import validators

logger = logging.getLogger("NovelForge.Compiler")


# ============================================================================
# EPUB COMPILER
# ============================================================================

class EPUBCompiler:
    """
    Compile CSV chapter files into a formatted EPUB eBook.
    Includes validation, metadata, styling, and error recovery.
    """
    
    def __init__(self, novel_name: str, output_folder: Path):
        """
        Initialize compiler.
        
        Args:
            novel_name: Novel title
            output_folder: Folder containing chapter CSVs
        """
        self.novel_name = novel_name
        self.output_folder = Path(output_folder)
        self.manifest_manager = ManifestManager()
        self.error_summary = ErrorSummary("EPUB Compilation")
        
        logger.info(f"Initialized compiler for {novel_name}")
    
    def compile(
        self,
        output_filename: Optional[str] = None,
        author: str = cfg.EPUB_DEFAULT_AUTHOR,
        language: str = cfg.EPUB_DEFAULT_LANGUAGE,
    ) -> Optional[Path]:
        """
        Compile chapters into EPUB.
        
        Args:
            output_filename: Output filename (defaults to {novel_name}.epub)
            author: Author name
            language: Book language (e.g., 'en', 'fr')
        
        Returns:
            Path to created EPUB file, or None if failed
        """
        try:
            # Validate output path
            output_filename = output_filename or cfg.EPUB_TITLE_TEMPLATE.format(
                novel_name=self.novel_name.replace(' ', '_')
            )
            
            output_filename = validators.sanitize_filename(output_filename)
            output_path = self.output_folder / output_filename
            
            logger.info(f"Compiling EPUB: {self.novel_name}")
            logger.info(f"Output: {output_path}")
            
            # Get chapter files
            chapter_files = self._get_chapter_files()
            
            if not chapter_files:
                logger.error("No chapters found to compile")
                raise CompilerError("No chapters found in folder")
            
            logger.info(f"Found {len(chapter_files)} chapters")
            
            # Create EPUB book
            book = self._create_book(
                chapter_files,
                self.novel_name,
                author,
                language,
            )
            
            # Write EPUB file
            with SafeFileOperation(output_path, 'wb') as f:
                epub.write_epub(str(output_path), book, {})
            
            logger.info(f"EPUB compiled successfully: {output_path}")
            return output_path
        
        except CompilerError as e:
            logger.error(f"Compilation error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during compilation: {str(e)}")
            return None
    
    def _get_chapter_files(self) -> List[Path]:
        """
        Get sorted list of chapter CSV files.
        
        Returns:
            List of Path objects, sorted by chapter number
        """
        files = [
            f for f in self.output_folder.iterdir()
            if f.name.startswith('chapter_') and f.suffix == '.csv'
        ]
        
        # Sort by chapter number
        files.sort(key=lambda f: utils.extract_chapter_number_from_filename(f.name))
        
        return files
    
    def _create_book(
        self,
        chapter_files: List[Path],
        title: str,
        author: str,
        language: str,
    ) -> epub.EpubBook:
        """
        Create EPUB book with chapters.
        
        Args:
            chapter_files: List of chapter CSV file paths
            title: Book title
            author: Author name
            language: Language code
        
        Returns:
            epub.EpubBook object
        """
        book = epub.EpubBook()
        
        # Set metadata
        book.set_identifier(f'{title.replace(" ", "_")}_{len(chapter_files)}')
        book.set_title(title)
        book.set_language(language)
        book.add_author(author)
        
        # Add stylesheet
        nav_css = epub.EpubItem()
        nav_css.file_name = 'style/nav.css'
        nav_css.media_type = 'text/css'
        nav_css.content = cfg.EPUB_STYLESHEET
        book.add_item(nav_css)
        
        # Process chapters
        epub_chapters = []
        
        for chapter_file in chapter_files:
            try:
                chapter_num = utils.extract_chapter_number_from_filename(chapter_file.name)
                
                # Load chapter data
                result = utils.load_chapter_from_csv(chapter_file, logger)
                if not result:
                    self.error_summary.add_warning(
                        chapter_num,
                        f"Could not load chapter from {chapter_file.name}",
                    )
                    continue
                
                title, editor, body, enhanced = result
                
                # Validate chapter
                try:
                    validators.validate_chapter_data(chapter_num, title, editor, body)
                except validators.ValidationError as e:
                    self.error_summary.add_warning(chapter_num, str(e))
                    continue
                
                # Create chapter
                chapter_obj = self._create_chapter(
                    chapter_num,
                    title,
                    body,
                    editor,
                )
                
                if chapter_obj:
                    book.add_item(chapter_obj)
                    epub_chapters.append(chapter_obj)
                    self.error_summary.record_success()
            
            except Exception as e:
                chapter_num = utils.extract_chapter_number_from_filename(chapter_file.name)
                logger.error(f"Failed to process chapter {chapter_num}: {str(e)}")
                self.error_summary.add_error(chapter_num, e)
        
        if not epub_chapters:
            raise CompilerError("No valid chapters to add to EPUB")
        
        # Set table of contents and spine
        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + epub_chapters
        
        logger.info(f"Book created with {len(epub_chapters)} chapters")
        return book
    
    def _create_chapter(
        self,
        chapter_num: int,
        title: str,
        body: str,
        editor: str = "",
    ) -> Optional[epub.EpubHtml]:
        """
        Create an EPUB chapter object.
        
        Args:
            chapter_num: Chapter number
            title: Chapter title
            body: Chapter body text
            editor: Editor name (optional)
        
        Returns:
            epub.EpubHtml object or None if error
        """
        try:
            # Clean title
            chapter_title = title.strip()
            if not chapter_title:
                chapter_title = f"Chapter {chapter_num}"
            
            # Create chapter
            chapter = epub.EpubHtml()
            chapter.file_name = f'chapter_{chapter_num:04d}.xhtml'
            chapter.title = chapter_title
            chapter.lang = 'en'
            
            # Build content HTML
            content_parts = [
                f'<h1>{self._escape_html(chapter_title)}</h1>'
            ]
            
            # Add editor info if present
            if editor and editor.lower() != 'unknown':
                content_parts.append(
                    f'<p class="editor-note"><em>Edited by: {self._escape_html(editor)}</em></p>'
                )
            
            # Add paragraphs
            for para in body.split('\n'):
                para = para.strip()
                if para:
                    content_parts.append(
                        f'<p>{self._escape_html(para)}</p>'
                    )
            
            chapter.content = '\n'.join(content_parts)
            
            return chapter
        
        except Exception as e:
            logger.error(f"Failed to create chapter {chapter_num}: {str(e)}")
            return None
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        }
        for char, escaped in replacements.items():
            text = text.replace(char, escaped)
        return text
    
    def get_error_summary(self) -> str:
        """Get compilation error summary."""
        return self.error_summary.get_report()


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

def compile_epub(
    folder_path: Path,
    novel_title: str,
    output_filename: Optional[str] = None,
    author: str = cfg.EPUB_DEFAULT_AUTHOR,
    language: str = cfg.EPUB_DEFAULT_LANGUAGE,
) -> Optional[Path]:
    """
    Convenience function to compile EPUB from chapter CSVs.
    
    Args:
        folder_path: Path to folder with chapter CSVs
        novel_title: Novel title
        output_filename: Output filename
        author: Author name
        language: Language code
    
    Returns:
        Path to created EPUB or None if failed
    """
    try:
        compiler = EPUBCompiler(novel_title, folder_path)
        return compiler.compile(output_filename, author, language)
    except Exception as e:
        logger.error(f"Failed to compile EPUB: {str(e)}")
        return None


def validate_epub_chapters(folder_path: Path) -> bool:
    """
    Validate all chapters before compilation.
    
    Args:
        folder_path: Path to chapter CSVs
    
    Returns:
        True if all chapters are valid
    """
    folder_path = Path(folder_path)
    error_summary = ErrorSummary("Chapter Validation")
    
    for chapter_file in folder_path.glob("chapter_*.csv"):
        try:
            chapter_num = utils.extract_chapter_number_from_filename(chapter_file.name)
            
            result = utils.load_chapter_from_csv(chapter_file, logger)
            if not result:
                error_summary.add_error(chapter_num, Exception("Could not load"))
                continue
            
            title, editor, body, enhanced = result
            validators.validate_chapter_data(chapter_num, title, editor, body)
            error_summary.record_success()
        
        except validators.ValidationError as e:
            error_summary.add_error(chapter_num, e)
        except Exception as e:
            error_summary.add_error(chapter_num, e)
    
    logger.info(error_summary.get_report())
    return len(error_summary.errors) == 0