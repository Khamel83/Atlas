#!/usr/bin/env python3
"""
Extract newsletters 101-150 accessible private newsletters
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def extract_101_150_newsletters():
    """Extract newsletters 101-150"""
    
    print("⚡ EXTRACTING NEWSLETTERS 101-150")
    print("=" * 50)
    
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
    
    # Get private newsletters metadata
    print("\n📋 Getting private newsletters...")
    
    all_private = {}
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'folder': 'all', 'limit': 500}
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
                        all_private[bookmark_id] = {
                            'bookmark_id': bookmark_id,
                            'title': bookmark.get('title', 'Untitled'),
                            'url': bookmark_url,
                            'private_source': private_source,
                            'time': bookmark.get('time', 0)
                        }
            
            print(f"  ✅ Found {len(all_private)} private newsletters")
            
        else:
            print(f"  ❌ Failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return
    
    # Process newsletters 101-150
    newsletters_list = list(all_private.values())[100:150]
    print(f"\n🔄 Processing newsletters 101-150 ({len(newsletters_list)} newsletters)...")
    
    successful = 0
    extracted_content = {}
    
    for i, newsletter in enumerate(newsletters_list, 101):
        try:
            bookmark_id = newsletter['bookmark_id']
            title = newsletter['title']
            
            text_url = client.BASE_URL + "bookmarks/get_text"
            params = {'bookmark_id': bookmark_id}
            
            response = client.oauth.post(text_url, data=params)
            
            if response.status_code == 200:
                full_text = response.text
                
                if len(full_text.strip()) > 100:
                    extracted_content[bookmark_id] = {
                        **newsletter,
                        'full_text': full_text,
                        'content_length': len(full_text),
                        'extraction_status': 'success'
                    }
                    successful += 1
                    print(f"  ✅ {i}: {title[:50]}... ({len(full_text):,} chars)")
                else:
                    print(f"  ⚠️  {i}: {title[:50]}... (minimal content: {len(full_text)} chars)")
            else:
                print(f"  ❌ {i}: {title[:50]}... (API error: {response.status_code})")
            
            time.sleep(0.5)  # Minimal delay
            
        except Exception as e:
            print(f"  ❌ Error with newsletter {i}: {e}")
    
    print(f"\n📊 RESULTS: {successful}/{len(newsletters_list)} successful")
    
    # Convert to Atlas format
    converted = 0
    if extracted_content:
        print(f"🔄 Converting {len(extracted_content)} to Atlas format...")
        
        atlas_dirs = {
            'html': 'output/articles/html',
            'markdown': 'output/articles/markdown', 
            'metadata': 'output/articles/metadata'
        }
        
        for directory in atlas_dirs.values():
            os.makedirs(directory, exist_ok=True)
        
        for bookmark_id, content_data in extracted_content.items():
            try:
                import hashlib
                uid_source = f"private_101_150_{bookmark_id}_{content_data['title']}"
                atlas_uid = hashlib.md5(uid_source.encode('utf-8')).hexdigest()[:16]
                
                create_atlas_files(content_data, atlas_uid, atlas_dirs)
                converted += 1
                
            except Exception as e:
                print(f"    ❌ Error converting: {e}")
        
        print(f"  ✅ Converted {converted} newsletters to Atlas")
    
    # Save report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    report = {
        'extraction_timestamp': timestamp,
        'batch_range': '101-150',
        'target_count': len(newsletters_list),
        'successfully_extracted': len(extracted_content),
        'atlas_converted': converted,
        'extracted_newsletter_ids': list(extracted_content.keys()) if extracted_content else []
    }
    
    report_file = f"extract_101_150_newsletters_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Report saved: {report_file}")
    
    running_total = 100 + successful
    if successful > 0:
        print(f"🎉 SUCCESS: Extracted {successful} more newsletters!")
        print(f"📈 Total so far: {running_total} newsletters extracted")
        
        # Check if we're reaching the known limit
        if successful < 50:
            print(f"⚠️  Success rate dropping: {successful}/50 ({successful/50*100:.1f}%)")
            print(f"📊 May be approaching API content access limits around item 150")
    else:
        print(f"⚠️  No successful extractions in this batch")
        print(f"📊 This confirms API content limit is around item 100-150 range")
    
    return successful

def create_atlas_files(content_data, atlas_uid, atlas_dirs):
    """Create Atlas files"""
    
    title = content_data['title']
    full_text = content_data['full_text']
    bookmark_id = content_data['bookmark_id']
    
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
        <p><strong>Source:</strong> Private Newsletter (Batch 101-150)</p>
        <p><strong>Content Length:</strong> {len(full_text):,} characters</p>
        <p><strong>Bookmark ID:</strong> {bookmark_id}</p>
    </div>
    
    <div class="newsletter-content">
        <pre>{full_text}</pre>
    </div>
</body>
</html>"""
    
    # Create Markdown  
    markdown_content = f"""# {title}

**Source:** Private Newsletter (Batch 101-150)  
**Content Length:** {len(full_text):,} characters  
**Bookmark ID:** {bookmark_id}

---

{full_text}
"""
    
    # Create metadata
    metadata = {
        "uid": atlas_uid,
        "content_type": "private_newsletter_batch_101_150",
        "source": content_data['url'],
        "title": title,
        "status": "success",
        "date": datetime.now().isoformat(),
        "error": None,
        "content_path": f"output/articles/markdown/{atlas_uid}.md",
        "html_path": f"output/articles/html/{atlas_uid}.html",
        "fetch_method": "instapaper_api_batch_101_150_extraction",
        "fetch_details": {
            "bookmark_id": bookmark_id,
            "content_length": len(full_text),
            "successful": True,
            "extraction_batch": "batch_101_150"
        },
        "type_specific": {
            "bookmark_id": bookmark_id,
            "instapaper_time": content_data['time'],
            "is_private_content": True,
            "content_length": len(full_text)
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
    extract_101_150_newsletters()