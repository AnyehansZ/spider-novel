import os
import csv
import time
from google import genai
from google.genai import types
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from utils import logger
import utils

# ... (EnhanceAPI class remains the same) ...

def enhance_folder(folder_path):
    files = [f for f in os.listdir(folder_path) if f.startswith('chapter_') and f.endswith('.csv')]
    files.sort(key=utils.extract_chapter_number_from_filename)

    if not files:
        logger.warning("Enhancer called but no CSV files found.")
        return

    api = EnhanceAPI()
    
    # --- RICH PROGRESS BAR ---
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
        transient=True # Disappears when done
    ) as progress:
        
        task = progress.add_task("[cyan]Enhancing Chapters...", total=len(files))

        for filename in files:
            filepath = os.path.join(folder_path, filename)
            rows = []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                for row in reader: rows.append(row)
            
            if not rows or not headers: 
                progress.advance(task)
                continue
                
            if "Enhanced" not in headers:
                headers.append("Enhanced")
                for r in rows:
                    if len(r) < 4: r.append("False")
            
            title, editor, body, is_enhanced = rows[0][0], rows[0][1], rows[0][2], rows[0][3]
            
            if is_enhanced.lower() == 'true':
                progress.advance(task)
                continue
                
            # Update the progress bar text dynamically
            progress.update(task, description=f"[cyan]Enhancing: {title}...")
            logger.info(f"Sending {filename} to Gemini API...")
            
            enhanced_body = api.process_text(body)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow([title, editor, enhanced_body, "True"])
                
            logger.info(f"Successfully enhanced {filename}")
            progress.advance(task)
            time.sleep(2) # API Rate Limit protection
            
    # Print a single completion message to the UI
    from main import console
    console.print("[bold green]✅ AI Enhancement Complete![/bold green]")