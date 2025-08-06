#!/usr/bin/env python3
"""
Complete API extraction with proper continuous pagination
to get ALL bookmarks, not just the first 500
"""

import os
import json
import time
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient
from datetime import datetime

def complete_api_extraction():
    """Extract ALL bookmarks using proper continuous pagination"""
    
    load_dotenv()
    
    # Load credentials
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing Instapaper credentials in .env file")
        return
    
    print("🚀 COMPLETE API EXTRACTION WITH CONTINUOUS PAGINATION")
    print("=" * 60)
    
    # Initialize client
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    # Authenticate
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print()
    
    # Strategy: Extract from unread folder with continuous pagination
    # Since all bookmarks appear to be duplicated across folders,
    # we only need to extract from one folder completely
    
    folder = "unread"
    all_bookmarks = []
    seen_bookmark_ids = set()
    page = 1
    have_param = ""
    
    print(f"📚 Extracting ALL bookmarks from {folder} folder...")
    print("🔄 Using continuous pagination until no more bookmarks...")
    print()
    
    while True:
        print(f"  📄 Page {page}:", end=" ")
        
        try:
            url = client.BASE_URL + "bookmarks/list"
            params = {'limit': 500, 'folder': folder}
            
            # Add 'have' parameter for pagination (except first request)
            if have_param:
                params['have'] = have_param
            
            response = client.oauth.post(url, data=params)
            
            if response.status_code != 200:
                print(f"❌ Failed with status {response.status_code}")
                break
            
            bookmarks = response.json()
            
            if not bookmarks or len(bookmarks) == 0:
                print("✅ No more bookmarks - extraction complete!")
                break
            
            # Process bookmarks from this page
            new_bookmarks = 0
            new_bookmark_ids = []
            
            for bookmark in bookmarks:
                bookmark_id = bookmark.get('bookmark_id')
                
                if bookmark_id and bookmark_id not in seen_bookmark_ids:
                    all_bookmarks.append(bookmark)
                    seen_bookmark_ids.add(bookmark_id)
                    new_bookmark_ids.append(str(bookmark_id))
                    new_bookmarks += 1
            
            print(f"Retrieved {len(bookmarks)} bookmarks, {new_bookmarks} new")
            
            # If we got no new bookmarks, we're done
            if new_bookmarks == 0:
                print("✅ No new bookmarks found - extraction complete!")
                break
            
            # Prepare 'have' parameter for next request
            # Use all bookmark IDs we've seen so far
            all_seen_ids = [str(bid) for bid in seen_bookmark_ids]
            have_param = ','.join(all_seen_ids)
            
            page += 1
            
            # Rate limiting - be nice to the API
            time.sleep(1)
            
            # Safety check - don't run forever
            if page > 20:  # Should be way more than enough for ~1300 bookmarks
                print("⚠️  Safety limit reached (20 pages) - stopping")
                break
                
        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            break
    
    print()
    print(f"🎯 EXTRACTION COMPLETE!")
    print(f"  Total pages processed: {page - 1}")
    print(f"  Total unique bookmarks: {len(all_bookmarks)}")
    print()
    
    # Save the complete extraction
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"complete_api_extraction_{timestamp}.json"
    
    extraction_data = {
        'extraction_timestamp': timestamp,
        'total_bookmarks': len(all_bookmarks),
        'extraction_method': 'continuous_pagination',
        'folder_extracted': folder,
        'pages_processed': page - 1,
        'bookmarks': all_bookmarks
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extraction_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved complete extraction to: {output_file}")
    print()
    
    # Analysis
    print("📊 EXTRACTION ANALYSIS")
    print("-" * 40)
    
    # Count different types
    web_urls = 0
    private_content = 0
    no_url = 0
    
    for bookmark in all_bookmarks:
        url = bookmark.get('url', '').strip()
        if url.startswith('http'):
            web_urls += 1
        elif url.startswith('instapaper-private://'):
            private_content += 1
        else:
            no_url += 1
    
    print(f"  Web URLs (http/https): {web_urls}")
    print(f"  Private content: {private_content}")
    print(f"  No URL/Other: {no_url}")
    print(f"  Total: {len(all_bookmarks)}")
    print()
    
    # Compare with CSV
    print("📋 COMPARISON WITH CSV EXPORT")
    print("-" * 40)
    
    csv_file = "inputs/instapaper_export.csv"
    if os.path.exists(csv_file):
        import subprocess
        
        # Count web URLs in CSV
        try:
            result = subprocess.run(['grep', '-c', '^https://', csv_file], capture_output=True, text=True)
            csv_web_urls = int(result.stdout.strip()) if result.returncode == 0 else 0
            
            result2 = subprocess.run(['grep', '-c', 'instapaper-private://', csv_file], capture_output=True, text=True)
            csv_private = int(result2.stdout.strip()) if result2.returncode == 0 else 0
            
            print(f"  CSV web URLs: {csv_web_urls}")
            print(f"  CSV private content: {csv_private}")
            print(f"  API web URLs: {web_urls}")
            print(f"  API private content: {private_content}")
            print()
            
            if web_urls >= csv_web_urls * 0.8:  # 80% or better coverage
                print("  ✅ EXCELLENT coverage of web URLs!")
            elif web_urls >= csv_web_urls * 0.5:  # 50% or better
                print("  ✅ GOOD coverage of web URLs")
            else:
                print("  ⚠️  Lower coverage - may need more extraction")
                
        except Exception as e:
            print(f"  ❌ Could not compare with CSV: {e}")
    
    print()
    
    # Next steps
    print("🎯 NEXT STEPS")
    print("-" * 40)
    
    if len(all_bookmarks) > 1000:
        print("  ✅ SUCCESS! Got comprehensive bookmark collection")
        print("  🔄 Ready to convert to Atlas format")
        print(f"  📁 Use: {output_file}")
        print()
        print("  💡 Commands to run next:")
        print(f"     python3 convert_complete_extraction_to_atlas.py {output_file}")
    else:
        print("  ⚠️  May need to try different extraction strategies")
        print("  🔍 Consider extracting from multiple folders")
        print("  📊 Or use CSV processing as fallback")
    
    return output_file

if __name__ == '__main__':
    complete_api_extraction()