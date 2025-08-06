#!/usr/bin/env python3
"""
Extract ALL 394 accessible private newsletters from the API
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def extract_all_394_newsletters():
    """Extract all 394 accessible private newsletters"""
    
    print("🚀 EXTRACTING ALL 394 ACCESSIBLE PRIVATE NEWSLETTERS")
    print("=" * 70)
    
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
    
    # Step 1: Get ALL 394 private newsletters metadata
    print("\n📋 STEP 1: Collecting all 394 private newsletter metadata")
    print("-" * 50)
    
    all_private_newsletters = collect_all_private_metadata(client)
    
    if not all_private_newsletters:
        print("❌ No private newsletters found")
        return
    
    print(f"✅ Collected metadata for {len(all_private_newsletters)} private newsletters")
    
    # Step 2: Attempt content extraction for all 394
    print(f"\n🔄 STEP 2: Attempting content extraction for all {len(all_private_newsletters)} newsletters")
    print("-" * 50)
    
    extraction_results = extract_content_from_all(client, all_private_newsletters)
    
    # Step 3: Convert successful extractions to Atlas format
    print(f"\n🔄 STEP 3: Converting successful extractions to Atlas format")
    print("-" * 50)
    
    atlas_conversion_results = convert_to_atlas_format(extraction_results)
    
    # Step 4: Generate comprehensive report
    print(f"\n📊 STEP 4: Final results summary")
    print("-" * 50)
    
    generate_final_report(extraction_results, atlas_conversion_results)
    
    return extraction_results

def collect_all_private_metadata(client):
    """Collect metadata for all 394 private newsletters"""
    
    all_private = {}
    
    # Use the best strategy from our testing
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
                            'time': bookmark.get('time', 0),
                            'description': bookmark.get('description', ''),
                            'starred': bookmark.get('starred', 0),
                            'progress': bookmark.get('progress', 0),
                            'progress_timestamp': bookmark.get('progress_timestamp', 0)
                        }
            
            print(f"  ✅ Found {len(all_private)} private newsletters in API")
            
            # Show sample
            sample_titles = [newsletter['title'][:50] + "..." for newsletter in list(all_private.values())[:5]]
            print(f"  📋 Sample titles:")
            for i, title in enumerate(sample_titles, 1):
                print(f"    {i}. {title}")
                
        else:
            print(f"  ❌ API failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Error collecting metadata: {e}")
    
    return all_private

def extract_content_from_all(client, all_private_newsletters):
    """Attempt content extraction for all newsletters with different strategies"""
    
    newsletters_list = list(all_private_newsletters.values())
    total_count = len(newsletters_list)
    
    extraction_results = {
        'successful_extractions': {},
        'failed_extractions': {},
        'extraction_stats': {
            'total_attempted': total_count,
            'successful': 0,
            'failed': 0,
            'content_accessible': 0,
            'content_inaccessible': 0
        },
        'error_analysis': {}
    }
    
    print(f"🎯 Attempting content extraction for {total_count} newsletters...")
    
    # Try different batch strategies
    strategies = [
        ("items_0_150", newsletters_list[:150]),
        ("items_150_250", newsletters_list[150:250]),
        ("items_250_350", newsletters_list[250:350]),
        ("items_350_394", newsletters_list[350:])
    ]
    
    for strategy_name, newsletter_batch in strategies:
        print(f"\n  🧪 Strategy: {strategy_name} ({len(newsletter_batch)} newsletters)")
        
        batch_successful = 0
        batch_failed = 0
        
        for i, newsletter in enumerate(newsletter_batch):
            try:
                bookmark_id = newsletter['bookmark_id']
                title = newsletter['title']
                
                # Progress indicator
                if (i + 1) % 20 == 0:
                    print(f"    📊 {strategy_name}: {i + 1}/{len(newsletter_batch)} processed...")
                
                # Attempt content extraction
                text_url = client.BASE_URL + "bookmarks/get_text"
                params = {'bookmark_id': bookmark_id}
                
                response = client.oauth.post(text_url, data=params)
                
                if response.status_code == 200:
                    full_text = response.text
                    
                    if len(full_text.strip()) > 100:  # Substantial content
                        extraction_results['successful_extractions'][bookmark_id] = {
                            **newsletter,
                            'full_text': full_text,
                            'content_length': len(full_text),
                            'extraction_status': 'success',
                            'extraction_strategy': strategy_name
                        }
                        batch_successful += 1
                        extraction_results['extraction_stats']['content_accessible'] += 1
                        
                    else:
                        # Minimal content
                        extraction_results['failed_extractions'][bookmark_id] = {
                            **newsletter,
                            'error': f'minimal_content_{len(full_text)}_chars',
                            'extraction_strategy': strategy_name
                        }
                        batch_failed += 1
                        extraction_results['extraction_stats']['content_inaccessible'] += 1
                        
                else:
                    # API error
                    error_key = f"http_{response.status_code}"
                    extraction_results['error_analysis'][error_key] = extraction_results['error_analysis'].get(error_key, 0) + 1
                    
                    extraction_results['failed_extractions'][bookmark_id] = {
                        **newsletter,
                        'error': f'api_error_{response.status_code}',
                        'extraction_strategy': strategy_name
                    }
                    batch_failed += 1
                    extraction_results['extraction_stats']['content_inaccessible'] += 1
                
                # Rate limiting
                time.sleep(1.5)
                
            except Exception as e:
                extraction_results['failed_extractions'][bookmark_id] = {
                    **newsletter,
                    'error': f'exception_{str(e)}',
                    'extraction_strategy': strategy_name
                }
                batch_failed += 1
                extraction_results['extraction_stats']['content_inaccessible'] += 1
        
        # Strategy results
        success_rate = batch_successful / len(newsletter_batch) * 100 if newsletter_batch else 0
        print(f"    ✅ {strategy_name}: {batch_successful}/{len(newsletter_batch)} successful ({success_rate:.1f}%)")
        
        extraction_results['extraction_stats']['successful'] += batch_successful
        extraction_results['extraction_stats']['failed'] += batch_failed
    
    print(f"\n📊 OVERALL EXTRACTION RESULTS:")
    stats = extraction_results['extraction_stats']
    print(f"  🎯 Total attempted: {stats['total_attempted']}")
    print(f"  ✅ Successful extractions: {stats['successful']}")
    print(f"  ❌ Failed extractions: {stats['failed']}")
    print(f"  📊 Success rate: {stats['successful']/stats['total_attempted']*100:.1f}%")
    print(f"  💰 Content accessible: {stats['content_accessible']}")
    print(f"  🚫 Content inaccessible: {stats['content_inaccessible']}")
    
    # Error analysis
    if extraction_results['error_analysis']:
        print(f"\n🔍 ERROR BREAKDOWN:")
        for error_type, count in extraction_results['error_analysis'].items():
            print(f"    {error_type}: {count} newsletters")
    
    return extraction_results

def convert_to_atlas_format(extraction_results):
    """Convert successful extractions to Atlas format"""
    
    successful_extractions = extraction_results['successful_extractions']
    
    if not successful_extractions:
        print("  ⚠️  No successful extractions to convert")
        return {'converted': 0}
    
    atlas_dirs = {
        'html': 'output/articles/html',
        'markdown': 'output/articles/markdown',
        'metadata': 'output/articles/metadata'
    }
    
    # Ensure directories exist
    for directory in atlas_dirs.values():
        os.makedirs(directory, exist_ok=True)
    
    converted_count = 0
    
    print(f"  🔄 Converting {len(successful_extractions)} successful extractions...")
    
    for bookmark_id, content_data in successful_extractions.items():
        try:
            # Generate Atlas UID
            import hashlib
            uid_source = f"private_{bookmark_id}_{content_data['title']}"
            atlas_uid = hashlib.md5(uid_source.encode('utf-8')).hexdigest()[:16]
            
            # Create Atlas files
            create_atlas_files_enhanced(content_data, atlas_uid, atlas_dirs)
            converted_count += 1
            
            if converted_count % 20 == 0:
                print(f"    ✅ Converted {converted_count} newsletters to Atlas format...")
            
        except Exception as e:
            print(f"    ❌ Error converting {content_data['title']}: {e}")
    
    print(f"  ✅ Successfully converted {converted_count} newsletters to Atlas format")
    
    return {'converted': converted_count}

def create_atlas_files_enhanced(content_data, atlas_uid, atlas_dirs):
    """Create enhanced Atlas format files"""
    
    title = content_data['title']
    full_text = content_data['full_text']
    bookmark_id = content_data['bookmark_id']
    extraction_strategy = content_data.get('extraction_strategy', 'unknown')
    
    # Convert timestamp
    timestamp = content_data.get('time', 0)
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.isoformat()
    else:
        formatted_time = datetime.now().isoformat()
    
    # Create enhanced HTML
    html_text = full_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
    if html_text and not html_text.startswith('<'):
        html_text = f'<p>{html_text}</p>'
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="extraction-batch" content="394-newsletter-extraction">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> Private Newsletter (Instapaper API - Full Collection)</p>
        <p><strong>Date:</strong> {formatted_time}</p>
        <p><strong>Content Length:</strong> {len(full_text):,} characters</p>
        <p><strong>Extraction Strategy:</strong> {extraction_strategy}</p>
        <p><strong>Bookmark ID:</strong> {bookmark_id}</p>
    </div>
    
    <div class="newsletter-content">
        {html_text}
    </div>
</body>
</html>"""
    
    # Create enhanced Markdown
    markdown_content = f"""# {title}

**Source:** Private Newsletter (Instapaper API - Full Collection)  
**Date:** {formatted_time}  
**Content Length:** {len(full_text):,} characters  
**Extraction Strategy:** {extraction_strategy}  
**Bookmark ID:** {bookmark_id}

---

{full_text}
"""
    
    # Create enhanced metadata
    metadata = {
        "uid": atlas_uid,
        "content_type": "private_newsletter_full_collection",
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
        "fetch_method": "instapaper_api_394_collection_extraction",
        "fetch_details": {
            "bookmark_id": bookmark_id,
            "extraction_method": "bookmarks_get_text_full_collection",
            "extraction_strategy": extraction_strategy,
            "content_length": len(full_text),
            "successful": True,
            "extraction_batch": "394_newsletter_complete_collection"
        },
        "category_version": None,
        "last_tagged_at": None,
        "source_hash": str(bookmark_id),
        "type_specific": {
            "bookmark_id": bookmark_id,
            "instapaper_time": content_data['time'],
            "starred": bool(content_data['starred']),
            "is_private_content": True,
            "private_source": content_data['private_source'],
            "content_length": len(full_text),
            "extraction_strategy": extraction_strategy,
            "progress": content_data.get('progress', 0),
            "progress_timestamp": content_data.get('progress_timestamp', 0)
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

def generate_final_report(extraction_results, atlas_results):
    """Generate comprehensive final report"""
    
    stats = extraction_results['extraction_stats']
    
    print(f"🎯 FINAL 394 NEWSLETTER EXTRACTION REPORT")
    print("=" * 70)
    
    print(f"📊 EXTRACTION SUMMARY:")
    print(f"  🎯 Target: 394 private newsletters")
    print(f"  ✅ Content accessible: {stats['content_accessible']}")
    print(f"  ❌ Content inaccessible: {stats['content_inaccessible']}")
    print(f"  📈 Success rate: {stats['successful']/stats['total_attempted']*100:.1f}%")
    
    print(f"\n📁 ATLAS CONVERSION:")
    print(f"  ✅ Converted to Atlas format: {atlas_results['converted']}")
    
    # Calculate improvement
    previous_count = 137
    current_success = stats['content_accessible']
    improvement = current_success - previous_count
    
    print(f"\n🚀 IMPROVEMENT OVER PREVIOUS EXTRACTION:")
    print(f"  Previous successful: {previous_count}")
    print(f"  Current successful: {current_success}")
    print(f"  Additional newsletters: +{improvement}")
    print(f"  Total improvement: {improvement/previous_count*100:.1f}% increase")
    
    # Save comprehensive report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    final_report = {
        'extraction_timestamp': timestamp,
        'target_newsletters': 394,
        'extraction_results': extraction_results,
        'atlas_conversion': atlas_results,
        'improvement_analysis': {
            'previous_successful': previous_count,
            'current_successful': current_success,
            'additional_newsletters': improvement,
            'improvement_percentage': improvement/previous_count*100
        }
    }
    
    report_file = f"394_newsletter_extraction_complete_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Complete report saved: {report_file}")
    
    if current_success > previous_count:
        print(f"\n🎉 SUCCESS: Extracted {improvement} additional private newsletters!")
        print(f"✨ Your private newsletter collection has significantly improved!")
    else:
        print(f"\n📊 ANALYSIS: Need to investigate why only {current_success} were accessible")

if __name__ == '__main__':
    extract_all_394_newsletters()