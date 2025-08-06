#!/usr/bin/env python3
"""
Extract full content from private newsletters using Instapaper API
- Get private bookmark IDs from API responses  
- Use bookmarks/get_text to extract full newsletter content
- Convert to Atlas format with real content
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def extract_private_newsletter_content():
    """Extract full content from private newsletters using API bookmark IDs"""
    
    load_dotenv()
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing Instapaper credentials")
        return
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print()
    
    print("📧 EXTRACTING PRIVATE NEWSLETTER CONTENT")
    print("=" * 50)
    
    # Step 1: Collect all private bookmarks from API
    print("📁 Step 1: Collecting private bookmarks from API...")
    
    folders_to_check = ['unread', 'archive', 'starred', '2371999', '3816912']  # Include custom folders
    folder_names = ['Unread', 'Archive', 'Starred', 'Feedly', 'Stratechery']
    
    private_bookmarks = {}  # Deduplicate by bookmark_id
    
    for folder_key, folder_name in zip(folders_to_check, folder_names):
        print(f"  Checking {folder_name}...")
        
        try:
            url = client.BASE_URL + "bookmarks/list"
            params = {'limit': 500, 'folder': folder_key}
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                bookmarks = response.json()
                private_found = 0
                
                for bookmark in bookmarks:
                    if bookmark.get('type') == 'bookmark':
                        bookmark_url = bookmark.get('url', '')
                        private_source = bookmark.get('private_source', '')
                        bookmark_id = bookmark.get('bookmark_id')
                        
                        # Check if this is private content
                        is_private = ('instapaper-private' in bookmark_url or 
                                    private_source or 
                                    bookmark_url.startswith('instapaper://private'))
                        
                        if is_private and bookmark_id:
                            private_bookmarks[bookmark_id] = {
                                'bookmark_id': bookmark_id,
                                'title': bookmark.get('title', 'Untitled'),
                                'url': bookmark_url,
                                'private_source': private_source,
                                'time': bookmark.get('time', 0),
                                'folder': folder_name,
                                'description': bookmark.get('description', ''),
                                'starred': bookmark.get('starred', 0)
                            }
                            private_found += 1
                
                print(f"    Found {private_found} private items")
            
        except Exception as e:
            print(f"    Error checking {folder_name}: {e}")
        
        time.sleep(1.0)  # Conservative rate limiting
    
    total_private = len(private_bookmarks)
    print(f"\n📊 Total unique private bookmarks found: {total_private}")
    
    if total_private == 0:
        print("❌ No private content found in API responses")
        return
    
    print()
    
    # Step 2: Extract full content for each private bookmark
    print("📝 Step 2: Extracting full content using bookmarks/get_text...")
    
    successful_extractions = 0
    failed_extractions = 0
    extracted_content = {}
    
    for i, (bookmark_id, bookmark_info) in enumerate(private_bookmarks.items()):
        title = bookmark_info['title']
        print(f"  [{i+1}/{total_private}] {title[:50]}...")
        
        try:
            # Use bookmarks/get_text API
            text_url = client.BASE_URL + "bookmarks/get_text"
            params = {'bookmark_id': bookmark_id}
            
            response = client.oauth.post(text_url, data=params)
            
            if response.status_code == 200:
                full_text = response.text
                
                # Check if we got meaningful content (be more lenient for newsletters)
                if len(full_text.strip()) > 50:  # Lower threshold for newsletters
                    extracted_content[bookmark_id] = {
                        **bookmark_info,
                        'full_text': full_text,
                        'content_length': len(full_text),
                        'extraction_status': 'success'
                    }
                    successful_extractions += 1
                    print(f"    ✅ Success! Content: {len(full_text):,} chars")
                    
                    # Show preview for verification
                    preview = full_text.strip()[:100].replace('\n', ' ')
                    print(f"        Preview: {preview}...")
                else:
                    print(f"    ⚠️  Minimal content: {len(full_text)} chars")
                    failed_extractions += 1
            else:
                print(f"    ❌ API failed: {response.status_code}")
                failed_extractions += 1
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            failed_extractions += 1
        
        # Conservative rate limiting - 2 seconds between requests
        time.sleep(2.0)
        
        # Progress indicator every 5 items
        if (i + 1) % 5 == 0:
            print(f"    Progress: {i+1}/{total_private} processed...")
            time.sleep(1.0)  # Extra pause every 5 items
    
    print(f"\n📊 EXTRACTION RESULTS:")
    print(f"  ✅ Successful extractions: {successful_extractions}")
    print(f"  ❌ Failed extractions: {failed_extractions}")
    print(f"  📈 Success rate: {successful_extractions/total_private*100:.1f}%")
    
    if successful_extractions == 0:
        print("❌ No content extracted successfully")
        return
    
    print()
    
    # Step 3: Convert to Atlas format
    print("🔄 Step 3: Converting to Atlas format...")
    
    # Create Atlas directories
    atlas_dirs = {
        'html': 'output/articles/html',
        'markdown': 'output/articles/markdown',
        'metadata': 'output/articles/metadata'
    }
    
    for directory in atlas_dirs.values():
        os.makedirs(directory, exist_ok=True)
    
    converted_count = 0
    
    for bookmark_id, content_data in extracted_content.items():
        try:
            # Generate Atlas UID
            import hashlib
            uid_source = f"{bookmark_id}_{content_data['title']}"
            atlas_uid = hashlib.md5(uid_source.encode('utf-8')).hexdigest()[:16]
            
            # Create HTML content
            html_content = create_newsletter_html(content_data)
            
            # Create Markdown content  
            markdown_content = create_newsletter_markdown(content_data)
            
            # Create metadata
            metadata = create_newsletter_metadata(content_data, atlas_uid)
            
            # Write files
            with open(f"{atlas_dirs['html']}/{atlas_uid}.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            with open(f"{atlas_dirs['markdown']}/{atlas_uid}.md", 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
            with open(f"{atlas_dirs['metadata']}/{atlas_uid}.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            converted_count += 1
            
        except Exception as e:
            print(f"    ❌ Error converting {content_data['title']}: {e}")
    
    print(f"  ✅ Converted {converted_count} newsletters to Atlas format")
    
    # Save extraction report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = f"private_newsletter_extraction_report_{timestamp}.json"
    
    report_data = {
        'extraction_timestamp': timestamp,
        'total_private_found': total_private,
        'successful_extractions': successful_extractions,
        'failed_extractions': failed_extractions,
        'success_rate': successful_extractions/total_private*100,
        'atlas_files_created': converted_count,
        'extracted_content': extracted_content
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"  📋 Extraction report saved: {report_file}")
    
    print()
    print("🎉 PRIVATE NEWSLETTER EXTRACTION COMPLETE!")
    print(f"📊 Successfully extracted {successful_extractions} newsletters with full content")
    print(f"📁 {converted_count} Atlas files created")
    print(f"💡 These contain your actual newsletter content, not just placeholders!")

def create_newsletter_html(content_data):
    """Create HTML file for newsletter content"""
    
    title = content_data['title']
    full_text = content_data['full_text']
    folder = content_data['folder']
    
    # Convert timestamp
    timestamp = content_data.get('time', 0)
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        formatted_time = 'Unknown'
    
    # Convert plain text to HTML paragraphs
    html_text = full_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
    if html_text and not html_text.startswith('<'):
        html_text = f'<p>{html_text}</p>'
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> Private Newsletter Content</p>
        <p><strong>Folder:</strong> {folder}</p>
        <p><strong>Date:</strong> {formatted_time}</p>
        <p><strong>Content Length:</strong> {len(full_text):,} characters</p>
    </div>
    
    <div class="newsletter-content">
        {html_text}
    </div>
</body>
</html>"""

def create_newsletter_markdown(content_data):
    """Create Markdown file for newsletter content"""
    
    title = content_data['title']
    full_text = content_data['full_text']
    folder = content_data['folder']
    
    # Convert timestamp
    timestamp = content_data.get('time', 0)
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        formatted_time = 'Unknown'
    
    return f"""# {title}

**Source:** Private Newsletter Content  
**Folder:** {folder}  
**Date:** {formatted_time}  
**Content Length:** {len(full_text):,} characters

---

{full_text}
"""

def create_newsletter_metadata(content_data, atlas_uid):
    """Create Atlas metadata for newsletter"""
    
    timestamp = content_data.get('time', 0)
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        formatted_timestamp = dt.isoformat()
    else:
        formatted_timestamp = datetime.now().isoformat()
    
    return {
        "uid": atlas_uid,
        "content_type": "instapaper_newsletter",
        "source": content_data['url'],
        "title": content_data['title'],
        "status": "success",
        "date": formatted_timestamp,
        "error": None,
        "content_path": f"output/articles/markdown/{atlas_uid}.md",
        "html_path": f"output/articles/html/{atlas_uid}.html",
        "audio_path": None,
        "transcript_path": None,
        "tags": [],
        "notes": [],
        "fetch_method": "instapaper_api_private_content",
        "fetch_details": {
            "bookmark_id": content_data['bookmark_id'],
            "extraction_method": "bookmarks_get_text",
            "content_length": content_data['content_length'],
            "successful": True
        },
        "category_version": None,
        "last_tagged_at": None,
        "source_hash": str(content_data['bookmark_id']),
        "type_specific": {
            "bookmark_id": content_data['bookmark_id'],
            "instapaper_time": content_data['time'],
            "starred": bool(content_data['starred']),
            "folder": content_data['folder'],
            "is_private_content": True,
            "private_source": content_data['private_source'],
            "content_length": content_data['content_length']
        },
        "video_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

if __name__ == '__main__':
    extract_private_newsletter_content()