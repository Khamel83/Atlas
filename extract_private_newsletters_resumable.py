#!/usr/bin/env python3
"""
Resumable private newsletter extraction - processes in smaller batches
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def extract_private_newsletters_batch(batch_size=50, start_index=0):
    """Extract private newsletters in smaller batches"""
    
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
    print(f"🔄 Processing batch starting from index {start_index}")
    
    # Get private bookmarks (same logic as before)
    folders_to_check = ['unread']  # Just use unread since they're duplicated
    private_bookmarks = {}
    
    print("📁 Collecting private bookmarks...")
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': 'unread'}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            for bookmark in bookmarks:
                if bookmark.get('type') == 'bookmark':
                    bookmark_url = bookmark.get('url', '')
                    private_source = bookmark.get('private_source', '')
                    bookmark_id = bookmark.get('bookmark_id')
                    
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
                            'description': bookmark.get('description', ''),
                            'starred': bookmark.get('starred', 0)
                        }
        
    except Exception as e:
        print(f"❌ Error collecting bookmarks: {e}")
        return
    
    # Convert to list for indexing
    private_list = list(private_bookmarks.values())
    total_private = len(private_list)
    
    print(f"📊 Found {total_private} total private bookmarks")
    
    # Determine batch range
    end_index = min(start_index + batch_size, total_private)
    batch_items = private_list[start_index:end_index]
    
    print(f"🎯 Processing items {start_index} to {end_index-1} ({len(batch_items)} items)")
    
    if not batch_items:
        print("✅ No more items to process")
        return
    
    # Extract content for this batch
    extracted_content = {}
    successful = 0
    failed = 0
    
    for i, bookmark_info in enumerate(batch_items):
        actual_index = start_index + i
        bookmark_id = bookmark_info['bookmark_id']
        title = bookmark_info['title']
        
        print(f"  [{actual_index+1}/{total_private}] {title[:50]}...")
        
        try:
            text_url = client.BASE_URL + "bookmarks/get_text"
            params = {'bookmark_id': bookmark_id}
            
            response = client.oauth.post(text_url, data=params)
            
            if response.status_code == 200:
                full_text = response.text
                
                if len(full_text.strip()) > 50:
                    extracted_content[bookmark_id] = {
                        **bookmark_info,
                        'full_text': full_text,
                        'content_length': len(full_text),
                        'extraction_status': 'success'
                    }
                    successful += 1
                    print(f"    ✅ Success! {len(full_text):,} chars")
                else:
                    print(f"    ⚠️  Minimal content: {len(full_text)} chars")
                    failed += 1
            else:
                print(f"    ❌ API failed: {response.status_code}")
                failed += 1
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            failed += 1
        
        # Conservative rate limiting
        time.sleep(2.0)
    
    print(f"\n📊 BATCH RESULTS:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success rate: {successful/(successful+failed)*100:.1f}%")
    
    # Convert to Atlas format
    if extracted_content:
        print(f"\n🔄 Converting {len(extracted_content)} items to Atlas format...")
        
        atlas_dirs = {
            'html': 'output/articles/html',
            'markdown': 'output/articles/markdown',
            'metadata': 'output/articles/metadata'
        }
        
        for directory in atlas_dirs.values():
            os.makedirs(directory, exist_ok=True)
        
        converted = 0
        for bookmark_id, content_data in extracted_content.items():
            try:
                # Generate Atlas UID
                import hashlib
                uid_source = f"private_{bookmark_id}_{content_data['title']}"
                atlas_uid = hashlib.md5(uid_source.encode('utf-8')).hexdigest()[:16]
                
                # Create files
                create_atlas_files(content_data, atlas_uid, atlas_dirs)
                converted += 1
                
            except Exception as e:
                print(f"    ❌ Error converting {content_data['title']}: {e}")
        
        print(f"  ✅ Converted {converted} newsletters to Atlas format")
    
    # Save batch report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    batch_report_file = f"private_newsletter_batch_{start_index}-{end_index-1}_{timestamp}.json"
    
    batch_report = {
        'batch_timestamp': timestamp,
        'start_index': start_index,
        'end_index': end_index - 1,
        'items_processed': len(batch_items),
        'successful_extractions': successful,
        'failed_extractions': failed,
        'success_rate': successful/(successful+failed)*100 if (successful+failed) > 0 else 0,
        'extracted_content': extracted_content
    }
    
    with open(batch_report_file, 'w', encoding='utf-8') as f:
        json.dump(batch_report, f, indent=2, ensure_ascii=False)
    
    print(f"  📋 Batch report saved: {batch_report_file}")
    
    # Check if there are more items to process
    if end_index < total_private:
        print(f"\n🔄 More items remain. To continue:")
        print(f"     python3 extract_private_newsletters_resumable.py {end_index}")
    else:
        print(f"\n🎉 ALL PRIVATE NEWSLETTERS EXTRACTED!")
        print(f"📊 Total processed: {total_private} private newsletters")

def create_atlas_files(content_data, atlas_uid, atlas_dirs):
    """Create Atlas format files for newsletter"""
    
    title = content_data['title']
    full_text = content_data['full_text']
    
    # Convert timestamp
    timestamp = content_data.get('time', 0)
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.isoformat()
    else:
        formatted_time = datetime.now().isoformat()
    
    # Create HTML
    html_text = full_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
    if html_text and not html_text.startswith('<'):
        html_text = f'<p>{html_text}</p>'
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> Private Newsletter (Instapaper API)</p>
        <p><strong>Date:</strong> {formatted_time}</p>
        <p><strong>Content Length:</strong> {len(full_text):,} characters</p>
    </div>
    
    <div class="newsletter-content">
        {html_text}
    </div>
</body>
</html>"""
    
    # Create Markdown
    markdown_content = f"""# {title}

**Source:** Private Newsletter (Instapaper API)  
**Date:** {formatted_time}  
**Content Length:** {len(full_text):,} characters

---

{full_text}
"""
    
    # Create metadata
    metadata = {
        "uid": atlas_uid,
        "content_type": "instapaper_newsletter",
        "source": content_data['url'],
        "title": title,
        "status": "success",
        "date": formatted_time,
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
            "is_private_content": True,
            "private_source": content_data['private_source'],
            "content_length": content_data['content_length']
        },
        "video_id": None,
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
    import sys
    start_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    extract_private_newsletters_batch(batch_size=50, start_index=start_index)