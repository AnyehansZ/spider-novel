import os
import csv
import re
import logging

# --- LOGGING SETUP ---
# This will create 'novelforge.log' in your main folder.
logging.basicConfig(
    filename='novelforge.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("NovelForge")

def ensure_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(f"Created folder: {folder_path}")

def extract_chapter_number_from_filename(filename):
    match = re.search(r'chapter_(\d+)', filename)
    if match:
        return int(match.group(1))
    return 0

def get_downloaded_chapters(folder_path):
    if not os.path.exists(folder_path):
        return []
    files = [f for f in os.listdir(folder_path) if f.startswith('chapter_') and f.endswith('.csv')]
    return sorted([extract_chapter_number_from_filename(f) for f in files])

def save_chapter_to_csv(folder_path, chapter_num, title, edited_by, body_text, enhanced="False"):
    ensure_folder(folder_path)
    filename = os.path.join(folder_path, f"chapter_{chapter_num:04d}.csv")
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Edited By", "Chapter Body", "Enhanced"])
        writer.writerow([title, edited_by, body_text, enhanced])
    
    # Log silently instead of printing to terminal
    logger.info(f"Saved chapter {chapter_num}: {title} to {filename}")