import os
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

import enhancer
import compiler
from crawlers.xiaxuenovels import XiaXueCrawler
from utils import logger

console = Console()

CRAWLER_REGISTRY = {
    "xiaxuenovels.xyz": XiaXueCrawler,
    "www.xiaxuenovels.xyz": XiaXueCrawler
}

def setup_session():
    console.clear()
    console.print(Panel.fit("[bold magenta]✨ NovelForge ✨[/bold magenta]\n[cyan]Universal Light Novel Scraper & Enhancer[/cyan]"))
    
    while True:
        url = Prompt.ask("\n[bold yellow]Enter the URL of the first chapter[/bold yellow] (or 'q' to quit)")
        if url.lower() == 'q':
            return None, None, None

        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            path_parts = [p for p in parsed.path.split('/') if p]

            if domain not in CRAWLER_REGISTRY:
                console.print(f"[bold red]❌ Unsupported domain: {domain}[/bold red]")
                logger.error(f"User attempted unsupported domain: {domain}")
                continue

            novel_slug = path_parts[0]
            start_url = path_parts[-1]
            base_url = f"{parsed.scheme}://{domain}/{novel_slug}/"
            
            novel_name = novel_slug.replace('-', ' ').title()
            output_folder = os.path.join("novels", novel_slug)

            console.print(f"\n[bold green]✅ Site Detected:[/bold green] {domain}")
            console.print(f"[bold green]✅ Novel Name:[/bold green] {novel_name}")
            
            CrawlerClass = CRAWLER_REGISTRY[domain]
            crawler = CrawlerClass(novel_name, output_folder, base_url, start_url)
            
            logger.info(f"Session started for {novel_name} at {domain}")
            return crawler, output_folder, novel_name

        except Exception as e:
            console.print(f"[bold red]❌ Error parsing URL:[/bold red] {e}")

def check_api_key():
    current_key = os.environ.get("GOOGLE_API_KEY")
    if current_key:
        if Confirm.ask("[cyan]Found GOOGLE_API_KEY in environment. Use this key?[/cyan]"):
            return
    
    new_key = Prompt.ask("[bold yellow]🔑 Enter your Google Gemini API key[/bold yellow]", password=True)
    if new_key:
        os.environ["GOOGLE_API_KEY"] = new_key
        console.print("[green]✅ API key set for this session.[/green]")
        logger.info("Temporary API key loaded by user.")
    else:
        console.print("[bold red]⚠️ No API key entered. Enhancement may fail.[/bold red]")

def main():
    crawler, active_folder, active_novel_name = setup_session()
    if not crawler: return

    while True:
        menu_text = (
            f"[bold cyan]Active Novel:[/bold cyan] {active_novel_name}\n"
            f"[bold cyan]Output Folder:[/bold cyan] {active_folder}\n\n"
            "[1] 🚀 Run Full Auto-Pipeline (Crawl -> Fix -> Enhance -> EPUB)\n"
            "[2] 🕸️  Start / Resume Crawling\n"
            "[3] 🛠️  Check and Fix Missing Chapters\n"
            "[4] ✨ Enhance Downloaded CSVs (Gemini AI)\n"
            "[5] 📚 Compile CSVs to EPUB\n"
            "[0] ❌ Exit"
        )
        console.print("\n", Panel(menu_text, title="[bold magenta]Main Menu[/bold magenta]", expand=False))
        
        choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]", choices=["1", "2", "3", "4", "5", "0"])
        
        if choice == '1':
            crawler.run_crawler()
            crawler.check_and_fix_missing()
            check_api_key()
            enhancer.enhance_folder(active_folder)
            epub_name = f"{active_novel_name.replace(' ', '_')}.epub"
            compiler.compile_epub(active_folder, active_novel_name, epub_name)
            console.print("\n[bold space_after_emoji][green]🎉 Full Pipeline Complete![/green][/bold space_after_emoji]")
            
        elif choice == '2':
            crawler.run_crawler()
        elif choice == '3':
            crawler.check_and_fix_missing()
        elif choice == '4':
            check_api_key()
            enhancer.enhance_folder(active_folder)
        elif choice == '5':
            epub_name = f"{active_novel_name.replace(' ', '_')}.epub"
            compiler.compile_epub(active_folder, active_novel_name, epub_name)
        elif choice == '0':
            console.print("[bold cyan]Goodbye! Exiting NovelForge...[/bold cyan]")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Process manually interrupted.[/bold red]")