import os
import csv
from ebooklib import epub
import utils

def compile_epub(folder_path, novel_title, output_filename="Compiled_Novel.epub"):
    """
    PARAMETERS: 
    - folder_path (str): Directory with CSVs.
    - novel_title (str): Name of the book.
    - output_filename (str): Desired output file name.
    """
    print(f"\n--- Compiling EPUB: {novel_title} ---")
    files = [f for f in os.listdir(folder_path) if f.startswith('chapter_') and f.endswith('.csv')]
    files.sort(key=utils.extract_chapter_number_from_filename)

    if not files:
        print("No files to compile.")
        return

    book = epub.EpubBook()
    book.set_identifier(f'{novel_title.replace(" ", "_")}_{len(files)}')
    book.set_title(novel_title)
    book.set_language('en')
    book.add_author('Unknown')

    epub_chapters = []
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        chap_num = utils.extract_chapter_number_from_filename(filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # skip header
            row = next(reader, None)
            
        if not row: continue
        
        title, editor, body = row[0], row[1], row[2]
        indexed_title = f"Chapter {chap_num}: {title.replace(f'Chapter {chap_num}', '').strip(': ')}"
        
        c = epub.EpubHtml()
        c.file_name = f'chapter_{chap_num:04d}.xhtml'
        c.title = indexed_title
        
        content = f"<h1>{indexed_title}</h1>\n"
        if editor and editor.lower() != 'unknown':
            content += f"<p><em>Edited by: {editor}</em></p>\n"
            
        for para in body.split('\n'):
            if para.strip():
                content += f"<p>{para.strip()}</p>\n"
                
        c.content = content
        book.add_item(c)
        epub_chapters.append(c)

    book.toc = epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    style = '''
    @namespace url("http://www.w3.org/1999/xhtml");
    body { font-family: Georgia, serif; line-height: 1.6; margin: 1em; text-align: justify; }
    h1 { text-align: center; margin-bottom: 0.5em; font-size: 1.8em; page-break-before: always; }
    p { text-indent: 1.5em; margin-bottom: 0.5em; }
    '''
    
    nav_css = epub.EpubItem()
    nav_css.file_name = 'style/nav.css'
    nav_css.media_type = 'text/css'
    nav_css.content = style
    book.add_item(nav_css)
    book.spine = ['nav'] + epub_chapters

    output_path = os.path.join(folder_path, output_filename)
    epub.write_epub(output_path, book, {})
    print(f"✅ SUCCESS! EPUB created: {output_path}")