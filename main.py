"""
NovelForge - Universal Light Novel Crawler & AI Enhancer
Main entry point with integrated CLI and error handling.
"""

import os
import sys
import logging
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
except ImportError:
    print("ERROR: rich library not installed. Run: pip install rich")
    sys.exit(1)

# Import our modules
import config as cfg
import utils
import validators
from error_handler import (
    NovelForgeError,
    APIKeyError,
    ConfigurationError,
    ErrorContext,
)
from settings_manager import SettingsManager
from manifest_manager import ManifestManager, slugify_novel_name
from crawlers.xiaxuenovels import XiaXueCrawler
import enhancer
import compiler

# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize console and logging
console = Console()
utils.setup_logging(log_level=cfg.LOG_LEVEL)
logger = logging.getLogger("NovelForge.Main")

# Settings manager
settings = SettingsManager(cfg.CONFIG_FILE)

# Site registry mapping domain -> crawler class
CRAWLER_REGISTRY = {
    "xiaxuenovels.xyz": XiaXueCrawler,
    "www.xiaxuenovels.xyz": XiaXueCrawler,
}

logger.info("=" * 60)
logger.info("NovelForge Started")
logger.info("=" * 60)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class NovelForgeApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.crawler = None
        self.active_folder = None
        self.active_novel_name = None
        self.active_novel_slug = None
        self.manifest_manager = ManifestManager()
        
        logger.info("Application initialized")
    
    def show_welcome(self):
        """Display welcome screen."""
        console.clear()
        console.print(Panel.fit(
            "[bold magenta]✨ NovelForge ✨[/bold magenta]\n"
            "[cyan]Universal Light Novel Scraper & Enhancer[/cyan]",
            border_style="magenta"
        ))
    
    def setup_session(self) -> bool:
        """
        Setup a new crawling session.
        Prompts user for URL and initializes crawler.
        
        Returns:
            True if successful
        """
        console.print("\n[bold yellow]📖 Novel Setup[/bold yellow]")
        
        while True:
            url = Prompt.ask(
                "[yellow]Enter the URL of the first chapter[/yellow]",
                default="https://xiaxuenovels.xyz/my-novel/chapter-1"
            )
            
            if url.lower() == 'q':
                return False
            
            try:
                # Validate URL
                url = validators.validate_url(url)
                
                # Parse URL
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc
                path_parts = [p for p in parsed.path.split('/') if p]
                
                # Check if domain is supported
                if domain not in CRAWLER_REGISTRY:
                    console.print(f"[red]❌ Unsupported domain: {domain}[/red]")
                    logger.warning(f"Unsupported domain: {domain}")
                    continue
                
                # Extract novel info
                if len(path_parts) < 1:
                    console.print("[red]❌ Invalid URL format[/red]")
                    continue
                
                novel_slug = path_parts[0]
                start_url = path_parts[-1] if len(path_parts) > 1 else "chapter-1"
                base_url = f"{parsed.scheme}://{domain}/{novel_slug}/"
                
                # Create novel name from slug
                novel_name = novel_slug.replace('-', ' ').title()
                
                # Validate paths
                output_folder = cfg.NOVELS_DIR / novel_slug
                output_folder = validators.ensure_safe_directory(output_folder)
                
                # Create crawler
                CrawlerClass = CRAWLER_REGISTRY[domain]
                self.crawler = CrawlerClass(novel_name, output_folder, base_url, start_url)
                
                self.active_folder = output_folder
                self.active_novel_name = novel_name
                self.active_novel_slug = novel_slug
                
                console.print(f"\n[green]✅ Configuration Complete[/green]")
                console.print(f"   Novel: {novel_name}")
                console.print(f"   Domain: {domain}")
                console.print(f"   Folder: {output_folder}")
                
                logger.info(f"Session configured: {novel_name} at {domain}")
                return True
            
            except validators.ValidationError as e:
                console.print(f"[red]❌ Error: {str(e)}[/red]")
                logger.error(f"URL validation error: {str(e)}")
            
            except Exception as e:
                console.print(f"[red]❌ Error setting up session: {str(e)}[/red]")
                logger.error(f"Setup error: {str(e)}")
    
    def check_api_key(self) -> bool:
        """
        Ensure API key is configured.
        Uses settings manager for persistence.
        
        Returns:
            True if API key is available
        """
        current_key = settings.get_api_key()
        
        if current_key:
            if Confirm.ask(
                "[cyan]Found Google Gemini API key in settings. Use it?[/cyan]",
                default=True
            ):
                return True
        
        console.print("\n[bold yellow]🔑 Google Gemini API Key Required[/bold yellow]")
        console.print(
            "Get your free API key from: "
            "[bold]https://aistudio.google.com/app/apikey[/bold]"
        )
        
        new_key = Prompt.ask(
            "[yellow]Enter your Google Gemini API key[/yellow]",
            password=True
        )
        
        if not new_key:
            console.print("[yellow]⚠️  No API key entered. Skipping enhancement.[/yellow]")
            logger.warning("User skipped API key configuration")
            return False
        
        # Validate and save
        try:
            validators.validate_api_key(new_key, "Google Gemini")
            settings.set_api_key(new_key)
            console.print("[green]✅ API key saved to settings[/green]")
            logger.info("API key configured")
            return True
        
        except validators.ValidationError as e:
            console.print(f"[red]❌ Invalid API key: {str(e)}[/red]")
            logger.error(f"API key validation failed: {str(e)}")
            return False
    
    def show_main_menu(self) -> str:
        """
        Display main menu and get user choice.
        
        Returns:
            Menu choice (1-5, 0 to exit)
        """
        menu_text = (
            f"[bold cyan]Active Novel:[/bold cyan] {self.active_novel_name}\n"
            f"[bold cyan]Output Folder:[/bold cyan] {self.active_folder}\n\n"
            "[bold yellow]OPTIONS:[/bold yellow]\n"
            "[1] 🚀 Run Full Auto-Pipeline (Crawl→Fix→Enhance→EPUB)\n"
            "[2] 🕸️  Start / Resume Crawling\n"
            "[3] 🛠️  Check and Fix Missing Chapters\n"
            "[4] ✨ Enhance Downloaded Chapters (Gemini AI)\n"
            "[5] 📚 Compile Chapters to EPUB\n"
            "[6] ⚙️  Settings & Configuration\n"
            "[0] ❌ Exit NovelForge"
        )
        
        console.print("\n", Panel(menu_text, title="[bold magenta]Main Menu[/bold magenta]"))
        
        choice = Prompt.ask(
            "[bold yellow]Select an option[/bold yellow]",
            choices=["0", "1", "2", "3", "4", "5", "6"],
            default="0"
        )
        
        return choice
    
    def run_full_pipeline(self):
        """Run complete crawl->fix->enhance->compile pipeline."""
        console.print("\n[bold cyan]Starting Full Auto-Pipeline[/bold cyan]")
        
        try:
            # Step 1: Crawl
            console.print("\n[bold yellow]Step 1: Crawling Chapters[/bold yellow]")
            with ErrorContext("Crawling", raise_on_error=False):
                self.crawler.run_crawler()
                console.print("[green]✅ Crawling complete[/green]")
            
            # Step 2: Fix missing
            console.print("\n[bold yellow]Step 2: Checking & Fixing Missing Chapters[/bold yellow]")
            with ErrorContext("Missing chapter recovery", raise_on_error=False):
                self.crawler.check_and_fix_missing()
                console.print("[green]✅ Recovery complete[/green]")
            
            # Step 3: Enhance (if API key available)
            console.print("\n[bold yellow]Step 3: AI Enhancement[/bold yellow]")
            if self.check_api_key():
                try:
                    api = enhancer.EnhanceAPI(settings.get_api_key())
                    api.set_model(settings.get_model())
                    
                    batch_enhancer = enhancer.BatchEnhancer(api, self.active_novel_slug)
                    if batch_enhancer.enhance_folder(self.active_folder):
                        console.print("[green]✅ Enhancement complete[/green]")
                    else:
                        console.print("[yellow]⚠️  Some chapters could not be enhanced[/yellow]")
                
                except APIKeyError as e:
                    console.print(f"[yellow]⚠️  Skipping enhancement: {str(e)}[/yellow]")
                    logger.warning(f"Enhancement skipped: {str(e)}")
            else:
                console.print("[yellow]Skipping enhancement (no API key)[/yellow]")
            
            # Step 4: Compile
            console.print("\n[bold yellow]Step 4: EPUB Compilation[/bold yellow]")
            with ErrorContext("EPUB compilation", raise_on_error=False):
                epub_path = compiler.compile_epub(
                    self.active_folder,
                    self.active_novel_name,
                )
                
                if epub_path:
                    console.print(f"[green]✅ EPUB created: {epub_path}[/green]")
                    logger.info(f"EPUB created: {epub_path}")
                    
                    # Optional cleanup
                    if settings.get_cleanup_mode() == "Always":
                        self._cleanup_csv_files()
                    elif settings.get_cleanup_mode() == "Ask":
                        if Confirm.ask(
                            "[yellow]Delete raw CSV files?[/yellow]",
                            default=False
                        ):
                            self._cleanup_csv_files()
                else:
                    console.print("[red]❌ Failed to compile EPUB[/red]")
            
            console.print("\n[bold green]🎉 Pipeline Complete![/bold green]")
            logger.info("Full pipeline completed successfully")
        
        except Exception as e:
            console.print(f"[red]❌ Pipeline error: {str(e)}[/red]")
            logger.error(f"Pipeline failed: {str(e)}")
    
    def run_crawler_only(self):
        """Run crawling operation only."""
        console.print("\n[bold cyan]Starting Crawler[/bold cyan]")
        try:
            self.crawler.run_crawler()
            console.print("[green]✅ Crawling complete[/green]")
            logger.info("Crawling completed")
        except Exception as e:
            console.print(f"[red]❌ Crawl error: {str(e)}[/red]")
            logger.error(f"Crawl failed: {str(e)}")
    
    def run_fix_missing(self):
        """Run missing chapter recovery only."""
        console.print("\n[bold cyan]Checking & Fixing Missing Chapters[/bold cyan]")
        try:
            self.crawler.check_and_fix_missing()
            console.print("[green]✅ Recovery complete[/green]")
            logger.info("Missing chapter recovery completed")
        except Exception as e:
            console.print(f"[red]❌ Recovery error: {str(e)}[/red]")
            logger.error(f"Recovery failed: {str(e)}")
    
    def run_enhancement_only(self):
        """Run AI enhancement only."""
        console.print("\n[bold cyan]Running AI Enhancement[/bold cyan]")
        
        if not self.check_api_key():
            console.print("[red]❌ API key required for enhancement[/red]")
            return
        
        try:
            api = enhancer.EnhanceAPI(settings.get_api_key())
            api.set_model(settings.get_model())
            
            batch_enhancer = enhancer.BatchEnhancer(api, self.active_novel_slug)
            if batch_enhancer.enhance_folder(self.active_folder):
                console.print("[green]✅ Enhancement complete[/green]")
            else:
                console.print("[yellow]⚠️  Some chapters could not be enhanced[/yellow]")
            
            logger.info("Enhancement completed")
        
        except Exception as e:
            console.print(f"[red]❌ Enhancement error: {str(e)}[/red]")
            logger.error(f"Enhancement failed: {str(e)}")
    
    def run_compilation_only(self):
        """Run EPUB compilation only."""
        console.print("\n[bold cyan]Compiling EPUB[/bold cyan]")
        
        try:
            epub_path = compiler.compile_epub(
                self.active_folder,
                self.active_novel_name,
            )
            
            if epub_path:
                console.print(f"[green]✅ EPUB created: {epub_path}[/green]")
                logger.info(f"EPUB created: {epub_path}")
                
                # Optional cleanup
                if settings.get_cleanup_mode() == "Always":
                    self._cleanup_csv_files()
                elif settings.get_cleanup_mode() == "Ask":
                    if Confirm.ask("[yellow]Delete raw CSV files?[/yellow]"):
                        self._cleanup_csv_files()
            else:
                console.print("[red]❌ Failed to compile EPUB[/red]")
            
            logger.info("Compilation completed")
        
        except Exception as e:
            console.print(f"[red]❌ Compilation error: {str(e)}[/red]")
            logger.error(f"Compilation failed: {str(e)}")
    
    def show_settings_menu(self):
        """Display settings menu."""
        while True:
            console.clear()
            console.print(Panel.fit("[bold magenta]⚙️  Settings[/bold magenta]"))
            
            current_model = settings.get_model()
            current_cleanup = settings.get_cleanup_mode()
            has_api = settings.has_api_key()
            
            menu = (
                f"[bold cyan]Current Configuration:[/bold cyan]\n"
                f"  • AI Model: {current_model}\n"
                f"  • Cleanup Mode: {current_cleanup}\n"
                f"  • API Key: {'✓ Configured' if has_api else '✗ Not set'}\n\n"
                "[bold yellow]OPTIONS:[/bold yellow]\n"
                "[1] 🔑 Set/Update API Key\n"
                "[2] 🧠 Select AI Model\n"
                "[3] 🧹 Configure Cleanup Behavior\n"
                "[0] 🔙 Back to Main Menu"
            )
            
            console.print(Panel(menu))
            
            choice = Prompt.ask("[yellow]Select option[/yellow]", choices=["0", "1", "2", "3"])
            
            if choice == "0":
                break
            elif choice == "1":
                self.check_api_key()
            elif choice == "2":
                self._select_model()
            elif choice == "3":
                self._select_cleanup_mode()
    
    def _select_model(self):
        """Let user select AI model."""
        console.print("\n[bold cyan]Select AI Model[/bold cyan]")
        
        models = list(SettingsManager.AVAILABLE_MODELS.items())
        for i, (model_id, description) in enumerate(models, 1):
            console.print(f"[{i}] {model_id}: {description}")
        
        choice = Prompt.ask(
            "[yellow]Select model[/yellow]",
            choices=[str(i) for i in range(1, len(models) + 1)]
        )
        
        selected_model = models[int(choice) - 1][0]
        settings.set_model(selected_model)
        console.print(f"[green]✅ Model set to: {selected_model}[/green]")
    
    def _select_cleanup_mode(self):
        """Let user select cleanup mode."""
        console.print("\n[bold cyan]Configure Cleanup Mode[/bold cyan]")
        
        modes = list(SettingsManager.CLEANUP_MODES.items())
        for i, (mode, description) in enumerate(modes, 1):
            console.print(f"[{i}] {mode}: {description}")
        
        choice = Prompt.ask(
            "[yellow]Select cleanup mode[/yellow]",
            choices=[str(i) for i in range(1, len(modes) + 1)]
        )
        
        selected_mode = modes[int(choice) - 1][0]
        settings.set_cleanup_mode(selected_mode)
        console.print(f"[green]✅ Cleanup mode set to: {selected_mode}[/green]")
    
    def _cleanup_csv_files(self):
        """Delete raw CSV files after successful EPUB compilation."""
        console.print("[yellow]Cleaning up CSV files...[/yellow]")
        
        for csv_file in self.active_folder.glob("chapter_*.csv"):
            try:
                csv_file.unlink()
                logger.info(f"Deleted {csv_file.name}")
            except Exception as e:
                logger.warning(f"Could not delete {csv_file.name}: {str(e)}")
        
        console.print("[green]✅ Cleanup complete[/green]")
    
    def run(self):
        """Main application loop."""
        self.show_welcome()
        
        # Setup session
        if not self.setup_session():
            console.print("[cyan]Goodbye![/cyan]")
            return
        
        # Main menu loop
        while True:
            choice = self.show_main_menu()
            
            if choice == "0":
                console.print("[bold cyan]Goodbye! Exiting NovelForge...[/bold cyan]")
                logger.info("Application closed normally")
                break
            elif choice == "1":
                self.run_full_pipeline()
            elif choice == "2":
                self.run_crawler_only()
            elif choice == "3":
                self.run_fix_missing()
            elif choice == "4":
                self.run_enhancement_only()
            elif choice == "5":
                self.run_compilation_only()
            elif choice == "6":
                self.show_settings_menu()


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Application entry point."""
    try:
        app = NovelForgeApp()
        app.run()
    except KeyboardInterrupt:
        console.print("\n[bold red]⚠️  Process interrupted by user[/bold red]")
        logger.warning("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal error: {str(e)}[/bold red]")
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()