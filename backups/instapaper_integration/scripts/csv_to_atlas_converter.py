#!/usr/bin/env python3
"""
Convert CSV export to Atlas format - the most reliable way to get ALL your bookmarks
"""

import os
import csv
import json
import hashlib
import time
from datetime import datetime
from urllib.parse import urlparse

def generate_unique_id(url, title, timestamp):
    """Generate a unique ID for the bookmark"""
    # Create a unique string from URL, title, and timestamp
    unique_string = f"{url}|{title}|{timestamp}"
    # Create MD5 hash and take first 16 characters
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()[:16]

def csv_to_atlas_converter():
    """Convert the complete CSV export to Atlas format"""
    
    print("🔄 CSV TO ATLAS CONVERTER")
    print("=" * 50)
    
    csv_file = "inputs/instapaper_export.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    # Create output directories
    output_dirs = [
        "output/articles/html",
        "output/articles/markdown", 
        "output/articles/metadata"
    ]
    
    for directory in output_dirs:
        os.makedirs(directory, exist_ok=True)
    
    print(f"📁 Reading CSV file: {csv_file}")
    
    # Read and process CSV
    bookmarks_processed = 0
    web_urls = 0
    private_content = 0
    errors = 0
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            print(f"📊 CSV Headers: {', '.join(reader.fieldnames)}")
            print()
            print("🔄 Processing bookmarks...")
            
            for row_num, row in enumerate(reader, 1):
                try:
                    url = row.get('URL', '').strip()
                    title = row.get('Title', 'Untitled').strip()
                    folder = row.get('Folder', 'Unknown').strip()
                    timestamp = row.get('Timestamp', '').strip()
                    selection = row.get('Selection', '').strip()
                    tags = row.get('Tags', '').strip()
                    
                    if not url:
                        continue
                    
                    # Generate unique ID
                    uid = generate_unique_id(url, title, timestamp)
                    
                    # Categorize content type
                    if url.startswith('http'):
                        web_urls += 1
                        content_type = "web_bookmark"
                        is_private = False
                        private_source = ""
                    elif url.startswith('instapaper-private://'):
                        private_content += 1
                        content_type = "private_content"
                        is_private = True
                        private_source = "instapaper_email"
                    else:
                        content_type = "unknown"
                        is_private = False
                        private_source = ""
                    
                    # Convert timestamp
                    try:
                        if timestamp.isdigit():
                            dt = datetime.fromtimestamp(int(timestamp))
                            formatted_timestamp = dt.isoformat()
                        else:
                            formatted_timestamp = datetime.now().isoformat()
                    except:
                        formatted_timestamp = datetime.now().isoformat()
                    
                    # Create HTML content
                    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> <a href="{url}">{url}</a></p>
        <p><strong>Folder:</strong> {folder}</p>
        <p><strong>Added:</strong> {formatted_timestamp}</p>
        {f'<p><strong>Tags:</strong> {tags}</p>' if tags and tags != '[]' else ''}
    </div>
    
    {f'<div class="selection"><h2>Selected Text:</h2><p>{selection}</p></div>' if selection else ''}
    
    <div class="content">
        <p><em>Content would need to be fetched separately for web URLs</em></p>
        {f'<p><strong>Private content:</strong> {private_source}</p>' if is_private else ''}
    </div>
</body>
</html>"""
                    
                    # Create Markdown content
                    markdown_content = f"""# {title}

**Source:** {url}
**Folder:** {folder}
**Added:** {formatted_timestamp}
{f'**Tags:** {tags}' if tags and tags != '[]' else ''}

{f'## Selected Text\\n{selection}\\n' if selection else ''}

## Content
{f'*Private content from {private_source}*' if is_private else '*Content would need to be fetched separately for web URLs*'}
"""
                    
                    # Create metadata JSON
                    metadata = {
                        "uid": uid,
                        "content_type": content_type,
                        "source": url,
                        "title": title,
                        "status": "converted_from_csv",
                        "date": formatted_timestamp,
                        "error": None,
                        "content_path": f"output/articles/markdown/{uid}.md",
                        "html_path": f"output/articles/html/{uid}.html",
                        "audio_path": None,
                        "transcript_path": None,
                        "tags": [tag.strip() for tag in tags.replace('[', '').replace(']', '').split(',') if tag.strip() and tag.strip() != '[]'],
                        "notes": [],
                        "fetch_method": "csv_export",
                        "fetch_details": {
                            "source": "instapaper_csv_export",
                            "csv_row": row_num,
                            "selection": selection
                        },
                        "category_version": None,
                        "last_tagged_at": None,
                        "source_hash": hashlib.md5(url.encode('utf-8')).hexdigest(),
                        "type_specific": {
                            "folder": folder,
                            "instapaper_timestamp": timestamp,
                            "is_private_content": is_private,
                            "private_source": private_source,
                            "selection": selection
                        },
                        "video_id": None,
                        "created_at": formatted_timestamp,
                        "updated_at": formatted_timestamp
                    }
                    
                    # Write files
                    with open(f"output/articles/html/{uid}.html", 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    with open(f"output/articles/markdown/{uid}.md", 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    
                    with open(f"output/articles/metadata/{uid}.json", 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    bookmarks_processed += 1
                    
                    # Progress indicator
                    if bookmarks_processed % 500 == 0:
                        print(f"  ✅ Processed {bookmarks_processed} bookmarks...")
                    
                except Exception as e:
                    errors += 1
                    print(f"  ❌ Error processing row {row_num}: {e}")
                    continue
    
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return
    
    print()
    print("🎯 CONVERSION COMPLETE!")
    print("=" * 50)
    print(f"  Total bookmarks processed: {bookmarks_processed:,}")
    print(f"  Web URLs: {web_urls:,}")
    print(f"  Private content: {private_content:,}")
    print(f"  Errors: {errors}")
    print()
    
    # Create summary report
    report_file = f"csv_to_atlas_conversion_report_{timestamp_str}.txt"
    
    report_content = f"""CSV TO ATLAS CONVERSION REPORT
==================================================

Conversion Date: {timestamp_str}
Total Bookmarks Processed: {bookmarks_processed:,}
Success Rate: {(bookmarks_processed/(bookmarks_processed+errors)*100):.1f}%

Content Breakdown:
  Web URLs: {web_urls:,}
  Private Content Items: {private_content:,}
  Errors: {errors}

Files Created:
  HTML files: output/articles/html/*.html
  Markdown files: output/articles/markdown/*.md
  Metadata files: output/articles/metadata/*.json

Notes:
- Web URLs converted to Atlas format but content not fetched
- Private content marked appropriately
- All original metadata preserved
- Ready for further processing if needed
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"📄 Conversion report saved: {report_file}")
    print()
    print("📁 FILES CREATED:")
    print(f"  📄 {bookmarks_processed:,} HTML files in output/articles/html/")
    print(f"  📝 {bookmarks_processed:,} Markdown files in output/articles/markdown/")
    print(f"  📊 {bookmarks_processed:,} Metadata files in output/articles/metadata/")
    print()
    print("✅ Your complete Instapaper collection is now in Atlas format!")

if __name__ == '__main__':
    csv_to_atlas_converter()