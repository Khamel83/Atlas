#!/usr/bin/env python3
"""
Extract the additional 28 pieces of content found in starred and archive folders
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def extract_additional_28_content():
    """Extract the 28 additional pieces found in maximization test"""
    
    print("⚡ EXTRACTING ADDITIONAL 28 PIECES OF CONTENT")
    print("=" * 60)
    
    load_dotenv()
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    
    # Extract starred folder content
    print(f"\n⭐ EXTRACTING STARRED FOLDER CONTENT")
    print("-" * 40)
    starred_extracted = extract_starred_content(client)
    
    # Extract archive folder content  
    print(f"\n🗃️  EXTRACTING ARCHIVE FOLDER CONTENT")
    print("-" * 40)
    archive_extracted = extract_archive_content(client)
    
    # Combine and convert to Atlas
    all_extracted = {**starred_extracted, **archive_extracted}
    
    if all_extracted:
        print(f"\n🔄 Converting {len(all_extracted)} items to Atlas format...")
        
        atlas_dirs = {
            'html': 'output/articles/html',
            'markdown': 'output/articles/markdown',
            'metadata': 'output/articles/metadata'
        }
        
        for directory in atlas_dirs.values():
            os.makedirs(directory, exist_ok=True)
        
        converted = 0
        for bookmark_id, content_data in all_extracted.items():
            try:
                import hashlib
                uid_source = f"additional_{bookmark_id}_{content_data['title']}"
                atlas_uid = hashlib.md5(uid_source.encode('utf-8')).hexdigest()[:16]
                
                create_atlas_files(content_data, atlas_uid, atlas_dirs)
                converted += 1
                
            except Exception as e:
                print(f"    ❌ Error converting {content_data.get('title', 'Unknown')}: {e}")
        
        print(f"  ✅ Converted {converted} additional items to Atlas")
    
    # Final summary
    print(f"\n🎯 ADDITIONAL EXTRACTION COMPLETE!")
    print("=" * 60)
    print(f"  ⭐ Starred content: {len(starred_extracted)} items")
    print(f"  🗃️  Archive content: {len(archive_extracted)} items")
    print(f"  📁 Total additional: {len(all_extracted)} items")
    print(f"  🎉 Grand total newsletters: 138 + {len(all_extracted)} = {138 + len(all_extracted)}")
    
    # Save extraction report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    report = {
        'extraction_timestamp': timestamp,
        'starred_extracted': len(starred_extracted),
        'archive_extracted': len(archive_extracted),
        'total_additional': len(all_extracted),
        'running_total': 138 + len(all_extracted),
        'extracted_items': {
            bookmark_id: {
                'title': data['title'],
                'content_length': data['content_length'],
                'folder': data['folder']
            } for bookmark_id, data in all_extracted.items()
        }
    }
    
    report_file = f"additional_28_extraction_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"  📄 Report saved: {report_file}")
    
    return len(all_extracted)

def extract_starred_content(client):
    """Extract content from starred folder"""
    
    extracted_content = {}
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'folder': 'starred', 'limit': 500}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            print(f"  📊 Found {len(bookmarks)} starred bookmarks")
            
            for i, bookmark in enumerate(bookmarks):
                if bookmark.get('type') == 'bookmark':
                    bookmark_id = bookmark.get('bookmark_id')
                    title = bookmark.get('title', 'Untitled')
                    
                    if bookmark_id:
                        # Test content extraction
                        text_url = client.BASE_URL + "bookmarks/get_text"
                        text_params = {'bookmark_id': bookmark_id}
                        text_response = client.oauth.post(text_url, data=text_params)
                        
                        if text_response.status_code == 200:
                            content = text_response.text
                            if len(content.strip()) > 100:
                                extracted_content[bookmark_id] = {
                                    'bookmark_id': bookmark_id,
                                    'title': title,
                                    'url': bookmark.get('url', ''),
                                    'full_text': content,
                                    'content_length': len(content),
                                    'folder': 'starred',
                                    'time': bookmark.get('time', 0)
                                }
                                print(f"    ✅ {len(extracted_content)}: {title[:50]}... ({len(content):,} chars)")
                        
                        time.sleep(0.3)  # Rate limiting
                        
                        # Stop if we get more than expected
                        if len(extracted_content) >= 25:
                            break
            
            print(f"  📊 Starred extraction: {len(extracted_content)} items with content")
            
    except Exception as e:
        print(f"  ❌ Starred extraction error: {e}")
    
    return extracted_content

def extract_archive_content(client):
    """Extract content from archive folder"""
    
    extracted_content = {}
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'folder': 'archive', 'limit': 500}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            print(f"  📊 Found {len(bookmarks)} archive bookmarks")
            
            for i, bookmark in enumerate(bookmarks):
                if bookmark.get('type') == 'bookmark':
                    bookmark_id = bookmark.get('bookmark_id')
                    title = bookmark.get('title', 'Untitled')
                    
                    if bookmark_id:
                        # Test content extraction
                        text_url = client.BASE_URL + "bookmarks/get_text"
                        text_params = {'bookmark_id': bookmark_id}
                        text_response = client.oauth.post(text_url, data=text_params)
                        
                        if text_response.status_code == 200:
                            content = text_response.text
                            if len(content.strip()) > 100:
                                extracted_content[bookmark_id] = {
                                    'bookmark_id': bookmark_id,
                                    'title': title,
                                    'url': bookmark.get('url', ''),
                                    'full_text': content,
                                    'content_length': len(content),
                                    'folder': 'archive',
                                    'time': bookmark.get('time', 0)
                                }
                                print(f"    ✅ {len(extracted_content)}: {title[:50]}... ({len(content):,} chars)")
                        
                        time.sleep(0.3)  # Rate limiting
                        
                        # Stop if we get more than expected
                        if len(extracted_content) >= 15:
                            break
            
            print(f"  📊 Archive extraction: {len(extracted_content)} items with content")
            
    except Exception as e:
        print(f"  ❌ Archive extraction error: {e}")
    
    return extracted_content

def create_atlas_files(content_data, atlas_uid, atlas_dirs):
    """Create Atlas files"""
    
    title = content_data['title']
    full_text = content_data['full_text']
    bookmark_id = content_data['bookmark_id']
    folder = content_data['folder']
    
    # Create HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> Additional Content ({folder.title()} Folder)</p>
        <p><strong>Content Length:</strong> {len(full_text):,} characters</p>
        <p><strong>Bookmark ID:</strong> {bookmark_id}</p>
        <p><strong>Extraction:</strong> Maximization Discovery</p>
    </div>
    
    <div class="content">
        <pre>{full_text}</pre>
    </div>
</body>
</html>"""
    
    # Create Markdown  
    markdown_content = f"""# {title}

**Source:** Additional Content ({folder.title()} Folder)  
**Content Length:** {len(full_text):,} characters  
**Bookmark ID:** {bookmark_id}  
**Extraction:** Maximization Discovery

---

{full_text}
"""
    
    # Create metadata
    metadata = {
        "uid": atlas_uid,
        "content_type": f"instapaper_{folder}_additional_content",
        "source": content_data['url'],
        "title": title,
        "status": "success",
        "date": datetime.now().isoformat(),
        "error": None,
        "content_path": f"output/articles/markdown/{atlas_uid}.md",
        "html_path": f"output/articles/html/{atlas_uid}.html",
        "fetch_method": f"instapaper_api_{folder}_folder_maximization",
        "fetch_details": {
            "bookmark_id": bookmark_id,
            "content_length": len(full_text),
            "successful": True,
            "extraction_batch": "maximization_discovery",
            "folder": folder
        },
        "type_specific": {
            "bookmark_id": bookmark_id,
            "instapaper_time": content_data['time'],
            "folder": folder,
            "content_length": len(full_text),
            "discovery_method": "folder_deep_dive"
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Write files
    with open(f"{atlas_dirs['html']}/{atlas_uid}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    with open(f"{atlas_dirs['markdown']}/{atlas_uid}.md", 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    with open(f"{atlas_dirs['metadata']}/{atlas_uid}.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    extract_additional_28_content()