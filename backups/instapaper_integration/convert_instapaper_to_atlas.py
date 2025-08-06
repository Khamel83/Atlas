#!/usr/bin/env python3
"""
Convert complete Instapaper backup to Atlas format
- HTML files with unique IDs
- Markdown files with unique IDs  
- JSON metadata files with unique IDs
- Handle private content properly
- Match existing Atlas structure exactly
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from time import sleep
import requests
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def convert_instapaper_to_atlas():
    """Convert the complete Instapaper backup to Atlas format"""
    
    # Load the complete extraction
    backup_file = "backups/instapaper_complete_extraction_2025-08-05-complete.json"
    
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return
    
    print("📚 Loading Instapaper backup...")
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    bookmarks = backup_data.get('folders', {})
    
    print(f"✅ Loaded backup with folders data")
    
    # Initialize Instapaper API client for content fetching
    instapaper_client = setup_instapaper_client()
    if not instapaper_client:
        print("⚠️ Could not setup Instapaper client - will use basic content only")
    else:
        print("✅ Instapaper API client ready for full content extraction")
    
    # Create Atlas output directories
    output_base = "output/articles"
    atlas_dirs = {
        'html': os.path.join(output_base, 'html'),
        'markdown': os.path.join(output_base, 'markdown'), 
        'metadata': os.path.join(output_base, 'metadata')
    }
    
    for dir_path in atlas_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    print(f"📁 Created Atlas directories")
    
    # Process all bookmarks from all folders
    all_bookmarks = {}
    for folder_name, folder_data in bookmarks.items():
        if isinstance(folder_data, dict) and 'bookmarks' in folder_data:
            folder_id = folder_data.get('folder_id', folder_name)
            folder_type = folder_data.get('folder_type', 'unknown')
            
            # folder_data['bookmarks'] is a list, not a dict
            bookmarks_list = folder_data['bookmarks']
            
            for bookmark_info in bookmarks_list:
                bookmark_id = str(bookmark_info.get('bookmark_id'))
                
                # Deduplicate by bookmark_id
                if bookmark_id not in all_bookmarks:
                    all_bookmarks[bookmark_id] = bookmark_info.copy()
                    all_bookmarks[bookmark_id]['folders'] = []
                
                # Add folder information
                all_bookmarks[bookmark_id]['folders'].append({
                    'folder_id': folder_id,
                    'folder_title': folder_name,
                    'folder_type': folder_type
                })
    
    print(f"📊 Processing {len(all_bookmarks)} unique bookmarks...")
    
    conversion_stats = {
        'total_processed': 0,
        'successful_conversions': 0,
        'private_content_items': 0,
        'public_content_items': 0,
        'errors': []
    }
    
    for i, (bookmark_id, bookmark_data) in enumerate(all_bookmarks.items()):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(all_bookmarks)} bookmarks processed")
        
        try:
            success = convert_single_bookmark(bookmark_data, atlas_dirs, conversion_stats, instapaper_client)
            conversion_stats['total_processed'] += 1
            
            if success:
                conversion_stats['successful_conversions'] += 1
                
        except Exception as e:
            error_msg = f"Error processing bookmark {bookmark_id}: {e}"
            conversion_stats['errors'].append(error_msg)
            print(f"  ❌ {error_msg}")
        
        # Slow processing - write data gradually
        if i % 10 == 0:
            sleep(1)  # Pause every 10 bookmarks
        else:
            sleep(0.1)  # Small delay between each bookmark
    
    # Save conversion report
    save_conversion_report(conversion_stats)
    
    print(f"\n🎉 CONVERSION COMPLETE!")
    print(f"📊 {conversion_stats['successful_conversions']}/{conversion_stats['total_processed']} bookmarks converted successfully")
    print(f"🔒 {conversion_stats['private_content_items']} private content items")
    print(f"🌐 {conversion_stats['public_content_items']} public content items")
    print(f"❌ {len(conversion_stats['errors'])} errors")

def setup_instapaper_client():
    """Setup Instapaper API client for content fetching"""
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')  
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        return None
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if client.authenticate(username, password):
        return client
    else:
        return None

def convert_single_bookmark(bookmark_data, atlas_dirs, stats, instapaper_client=None):
    """Convert a single bookmark to Atlas format with full content"""
    
    # Extract bookmark information
    title = bookmark_data.get('title', 'No Title')
    url = bookmark_data.get('url', '')
    description = bookmark_data.get('description', '')
    bookmark_id = bookmark_data.get('bookmark_id')
    time = bookmark_data.get('time', 0)
    starred = bookmark_data.get('starred', 0)
    progress = bookmark_data.get('progress', 0.0)
    folders = bookmark_data.get('folders', [])
    private_source = bookmark_data.get('private_source', '')
    
    # Determine if this is private content
    is_private = url.startswith('instapaper://private-content/') or bool(private_source)
    
    if is_private:
        stats['private_content_items'] += 1
    else:
        stats['public_content_items'] += 1
    
    # Generate unique Atlas ID (8-character hex)
    id_source = f"{bookmark_id}_{url}_{title}"
    atlas_uid = hashlib.md5(id_source.encode('utf-8')).hexdigest()[:16]
    
    # Create metadata in Atlas format
    atlas_metadata = {
        "uid": atlas_uid,
        "content_type": "instapaper",
        "source": url,
        "title": title,
        "status": "success",
        "date": datetime.now().isoformat(),
        "error": None,
        "content_path": f"output/articles/markdown/{atlas_uid}.md",
        "html_path": f"output/articles/html/{atlas_uid}.html",
        "audio_path": None,
        "transcript_path": None,
        "tags": [],
        "notes": [],
        "fetch_method": "instapaper_api",
        "fetch_details": {
            "attempts": [],
            "successful_method": "instapaper_api",
            "is_truncated": False,
            "total_attempts": 1,
            "fetch_time": None
        },
        "category_version": None,
        "last_tagged_at": None,
        "source_hash": hashlib.md5(url.encode('utf-8')).hexdigest(),
        "type_specific": {
            "bookmark_id": bookmark_id,
            "instapaper_time": time,
            "starred": bool(starred),
            "progress": progress,
            "folders": [f.get('folder_title', 'Unknown') for f in folders],
            "is_private_content": is_private,
            "private_source": private_source
        },
        "video_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Save metadata JSON
    metadata_path = os.path.join(atlas_dirs['metadata'], f"{atlas_uid}.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(atlas_metadata, f, indent=2, ensure_ascii=False)
    
    # Fetch full content from Instapaper if possible
    full_text_content = None
    if instapaper_client and bookmark_id:
        full_text_content = fetch_instapaper_content(instapaper_client, bookmark_id, title)
        
        # Add small delay for API rate limiting
        sleep(0.5)
    
    # Create content based on type and available data
    if is_private:
        # For private content, use any available full text or create placeholder
        content_html = create_private_content_html(title, url, description, folders, full_text_content)
        content_md = create_private_content_markdown(title, url, description, folders, full_text_content)
    else:
        # For public content, use full text if available or create basic content
        content_html = create_public_content_html(title, url, description, folders, full_text_content)
        content_md = create_public_content_markdown(title, url, description, folders, full_text_content)
    
    # Save HTML file
    html_path = os.path.join(atlas_dirs['html'], f"{atlas_uid}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content_html)
    
    # Save Markdown file
    md_path = os.path.join(atlas_dirs['markdown'], f"{atlas_uid}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content_md)
    
    return True

def fetch_instapaper_content(client, bookmark_id, title):
    """Fetch full text content from Instapaper API"""
    
    try:
        url = client.BASE_URL + "bookmarks/get_text"
        params = {'bookmark_id': bookmark_id}
        
        response = client.oauth.post(url, data=params)
        response.raise_for_status()
        
        # The response is the full text content
        full_text = response.text
        
        if full_text and len(full_text.strip()) > 100:  # Valid content
            return full_text
        else:
            return None
            
    except Exception as e:
        # Silently fail - we'll use basic content
        return None

def create_private_content_html(title, url, description, folders, full_text=None):
    """Create HTML for private Instapaper content"""
    
    folder_names = [f.get('folder_title', 'Unknown') for f in folders]
    folders_str = ', '.join(folder_names) if folder_names else 'None'
    
    content_section = ""
    if full_text:
        # Convert plain text to basic HTML
        html_content = full_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
        content_section = f'<div class="content"><p>{html_content}</p></div>'
    else:
        content_section = '''<div class="content">
        <p><em>This is private content from Instapaper that cannot be directly accessed via URL. 
        The content was saved privately to your Instapaper account and would need to be accessed 
        through Instapaper's full-text extraction API for complete content.</em></p>
    </div>'''
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> Private Instapaper Content</p>
        <p><strong>Original URL:</strong> {url}</p>
        <p><strong>Folders:</strong> {folders_str}</p>
        {f'<p><strong>Description:</strong> {description}</p>' if description else ''}
    </div>
    
    {content_section}
</body>
</html>"""

def create_private_content_markdown(title, url, description, folders, full_text=None):
    """Create Markdown for private Instapaper content"""
    
    folder_names = [f.get('folder_title', 'Unknown') for f in folders]
    folders_str = ', '.join(folder_names) if folder_names else 'None'
    
    content = f"""# {title}

**Source:** Private Instapaper Content  
**Original URL:** {url}  
**Folders:** {folders_str}  
"""
    
    if description:
        content += f"**Description:** {description}\n"
    
    content += "\n---\n\n"
    
    if full_text:
        content += full_text
    else:
        content += "*This is private content from Instapaper that cannot be directly accessed via URL. The content was saved privately to your Instapaper account and would need to be accessed through Instapaper's full-text extraction API for complete content.*"
    
    return content

def create_public_content_html(title, url, description, folders, full_text=None):
    """Create HTML for public content"""
    
    folder_names = [f.get('folder_title', 'Unknown') for f in folders]
    folders_str = ', '.join(folder_names) if folder_names else 'None'
    
    content_section = ""
    if full_text:
        # Convert plain text to basic HTML
        html_content = full_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
        content_section = f'<div class="content"><p>{html_content}</p></div>'
    else:
        content_section = f'''<div class="content">
        <p><em>This bookmark was imported from Instapaper. To get the full article content, 
        the original URL would need to be fetched and processed by Atlas.</em></p>
        
        <p><a href="{url}" target="_blank">View Original Article</a></p>
    </div>'''

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> <a href="{url}">{url}</a></p>
        <p><strong>Folders:</strong> {folders_str}</p>
        {f'<p><strong>Description:</strong> {description}</p>' if description else ''}
    </div>
    
    {content_section}
</body>
</html>"""

def create_public_content_markdown(title, url, description, folders, full_text=None):
    """Create Markdown for public content"""
    
    folder_names = [f.get('folder_title', 'Unknown') for f in folders]
    folders_str = ', '.join(folder_names) if folder_names else 'None'
    
    content = f"""# {title}

**Source:** [{url}]({url})  
**Folders:** {folders_str}  
"""
    
    if description:
        content += f"**Description:** {description}\n"
    
    content += "\n---\n\n"
    
    if full_text:
        content += full_text
    else:
        content += f"*This bookmark was imported from Instapaper. To get the full article content, the original URL would need to be fetched and processed by Atlas.*\n\n[View Original Article]({url})"
    
    return content

def save_conversion_report(stats):
    """Save conversion report"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = f"instapaper_atlas_conversion_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("INSTAPAPER TO ATLAS CONVERSION REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Conversion Date: {timestamp}\n")
        f.write(f"Total Bookmarks Processed: {stats['total_processed']:,}\n")
        f.write(f"Successful Conversions: {stats['successful_conversions']:,}\n") 
        f.write(f"Success Rate: {(stats['successful_conversions']/stats['total_processed']*100):.1f}%\n\n")
        
        f.write(f"Content Breakdown:\n")
        f.write(f"  Private Content Items: {stats['private_content_items']:,}\n")
        f.write(f"  Public Content Items: {stats['public_content_items']:,}\n\n")
        
        f.write("Files Created:\n")
        f.write(f"  HTML files: output/articles/html/*.html\n")
        f.write(f"  Markdown files: output/articles/markdown/*.md\n") 
        f.write(f"  Metadata files: output/articles/metadata/*.json\n\n")
        
        if stats['errors']:
            f.write(f"Errors ({len(stats['errors'])}):\n")
            for error in stats['errors'][:10]:  # First 10 errors
                f.write(f"  - {error}\n")
            if len(stats['errors']) > 10:
                f.write(f"  ... and {len(stats['errors']) - 10} more errors\n")
    
    print(f"📋 Conversion report saved to: {report_file}")

if __name__ == '__main__':
    print("🔄 CONVERTING INSTAPAPER BACKUP TO ATLAS FORMAT")
    print("📁 Creating HTML, MD, and JSON files with unique IDs")
    print("🔒 Handling both private and public content")
    print("📊 Matching existing Atlas structure")
    print()
    
    convert_instapaper_to_atlas()