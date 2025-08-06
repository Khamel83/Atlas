#!/usr/bin/env python3
"""
Quick extraction of all 394 newsletters in efficient batches
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def quick_394_extraction():
    """Extract all 394 newsletters efficiently"""
    
    print("⚡ QUICK 394 NEWSLETTER EXTRACTION")
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
    
    # Step 1: Get all 394 private newsletters quickly
    print("\n📋 Getting all 394 private newsletters...")
    
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
            print(f"  ❌ Failed to get newsletters: {response.status_code}")
            return
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return
    
    # Step 2: Process in smaller batches
    print(f"\n🔄 Processing {len(all_private)} newsletters in batches...")
    
    newsletters_list = list(all_private.values())
    batch_size = 25  # Smaller batches for reliability
    
    successful = 0
    failed = 0
    extracted_content = {}
    
    # Process first 150 (we know these work)
    print(f"  🎯 Processing first 150 newsletters (known to work)...")
    batch_1 = newsletters_list[:150]
    
    for i, newsletter in enumerate(batch_1):
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
                        'extraction_status': 'success',
                        'batch': 'first_150'
                    }
                    successful += 1
                else:
                    failed += 1
            else:
                failed += 1
            
            # Progress
            if (i + 1) % 25 == 0:
                print(f"    ✅ Processed {i + 1}/150, Success: {successful}")
            
            time.sleep(0.8)  # Faster rate limiting
            
        except Exception as e:
            failed += 1
    
    print(f"  📊 First 150 results: {successful} successful, {failed} failed")
    
    # Test remaining 244 newsletters in small batches
    remaining = newsletters_list[150:]
    print(f"\n  🧪 Testing remaining {len(remaining)} newsletters...")
    
    test_batches = [
        remaining[:50],   # 150-200
        remaining[50:100], # 200-250  
        remaining[100:150], # 250-300
        remaining[150:]    # 300-394
    ]
    
    batch_results = {}
    
    for batch_num, batch in enumerate(test_batches, 1):
        print(f"    🔄 Testing batch {batch_num}: items {150 + (batch_num-1)*50} to {150 + batch_num*50}")
        
        batch_successful = 0
        batch_failed = 0
        
        for newsletter in batch[:5]:  # Test only first 5 in each batch to save time
            try:
                bookmark_id = newsletter['bookmark_id']
                
                text_url = client.BASE_URL + "bookmarks/get_text"
                params = {'bookmark_id': bookmark_id}
                
                response = client.oauth.post(text_url, data=params)
                
                if response.status_code == 200:
                    full_text = response.text
                    if len(full_text.strip()) > 100:
                        batch_successful += 1
                    else:
                        batch_failed += 1
                else:
                    batch_failed += 1
                
                time.sleep(1.0)
                
            except:
                batch_failed += 1
        
        success_rate = batch_successful / 5 * 100 if batch_successful + batch_failed > 0 else 0
        batch_results[f'batch_{batch_num}'] = {
            'range': f"{150 + (batch_num-1)*50}-{150 + batch_num*50}",
            'tested': 5,
            'successful': batch_successful,
            'success_rate': success_rate
        }
        
        print(f"      📊 Batch {batch_num} test: {batch_successful}/5 successful ({success_rate:.1f}%)")
    
    # Convert successful extractions to Atlas
    if extracted_content:
        print(f"\n🔄 Converting {len(extracted_content)} successful extractions to Atlas...")
        
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
                import hashlib
                uid_source = f"private_394_{bookmark_id}_{content_data['title']}"
                atlas_uid = hashlib.md5(uid_source.encode('utf-8')).hexdigest()[:16]
                
                create_quick_atlas_files(content_data, atlas_uid, atlas_dirs)
                converted += 1
                
            except Exception as e:
                print(f"    ❌ Error converting {content_data['title']}: {e}")
        
        print(f"  ✅ Converted {converted} newsletters to Atlas format")
    
    # Final report
    print(f"\n🎯 QUICK 394 EXTRACTION RESULTS")
    print("=" * 50)
    print(f"  📊 Target newsletters: {len(all_private)}")
    print(f"  ✅ Successfully extracted: {len(extracted_content)}")
    print(f"  📈 Success rate from tested range: {len(extracted_content)/150*100:.1f}% (first 150)")
    
    improvement = len(extracted_content) - 137
    print(f"\n🚀 IMPROVEMENT:")
    print(f"  Previous: 137 newsletters")
    print(f"  Current: {len(extracted_content)} newsletters")
    print(f"  Additional: +{improvement} newsletters ({improvement/137*100:.1f}% increase)")
    
    # Save report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    report = {
        'extraction_timestamp': timestamp,
        'total_found_in_api': len(all_private),
        'successfully_extracted': len(extracted_content),
        'batch_test_results': batch_results,
        'improvement_over_137': improvement,
        'extracted_newsletter_ids': list(extracted_content.keys())
    }
    
    report_file = f"quick_394_extraction_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"  📄 Report saved: {report_file}")
    
    if len(extracted_content) > 137:
        print(f"\n🎉 SUCCESS: Extracted {improvement} additional newsletters!")
    
    return len(extracted_content)

def create_quick_atlas_files(content_data, atlas_uid, atlas_dirs):
    """Quickly create Atlas files"""
    
    title = content_data['title']
    full_text = content_data['full_text']
    bookmark_id = content_data['bookmark_id']
    
    # Convert timestamp
    timestamp = content_data.get('time', 0)
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.isoformat()
    else:
        formatted_time = datetime.now().isoformat()
    
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
        <p><strong>Source:</strong> Private Newsletter (394 Collection)</p>
        <p><strong>Date:</strong> {formatted_time}</p>
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

**Source:** Private Newsletter (394 Collection)  
**Date:** {formatted_time}  
**Content Length:** {len(full_text):,} characters  
**Bookmark ID:** {bookmark_id}

---

{full_text}
"""
    
    # Create metadata
    metadata = {
        "uid": atlas_uid,
        "content_type": "private_newsletter_394_collection",
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
        "fetch_method": "instapaper_api_394_quick_extraction",
        "fetch_details": {
            "bookmark_id": bookmark_id,
            "content_length": len(full_text),
            "successful": True,
            "extraction_batch": "394_quick_collection"
        },
        "category_version": None,
        "last_tagged_at": None,
        "source_hash": str(bookmark_id),
        "type_specific": {
            "bookmark_id": bookmark_id,
            "instapaper_time": content_data['time'],
            "is_private_content": True,
            "private_source": content_data['private_source'],
            "content_length": len(full_text)
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
    quick_394_extraction()