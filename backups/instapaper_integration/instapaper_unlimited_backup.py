#!/usr/bin/env python3
"""
Unlimited Instapaper backup - use proper 'have' parameter with hashes
"""

import json
import os
from time import sleep
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def get_all_bookmarks_unlimited():
    """Get ALL bookmarks using proper hash-based pagination"""
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')  
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing credentials in .env file")
        return []
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return []
    
    print("✅ Authentication successful")
    
    all_bookmarks = []
    seen_hashes = set()
    batch_count = 0
    
    # Keep fetching until we get no new bookmarks
    while True:
        batch_count += 1
        print(f"📥 Fetching batch {batch_count} (have {len(seen_hashes)} seen bookmarks)...")
        
        # Prepare API call
        url = client.BASE_URL + "bookmarks/list"
        params = {
            'limit': 500,  # Max allowed
        }
        
        # Add 'have' parameter with existing hashes for proper pagination
        if seen_hashes:
            # Instapaper expects comma-separated hash values
            params['have'] = ','.join(sorted(seen_hashes))
        
        try:
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                print(f"  ⚠️ Unexpected response format: {type(data)}")
                break
            
            # Filter bookmarks and extract hashes
            bookmarks = [item for item in data if item.get('type') == 'bookmark']
            
            if not bookmarks:
                print(f"  ✅ No more bookmarks found")
                break
            
            # Check for truly new bookmarks by hash
            new_bookmarks = []
            for bookmark in bookmarks:
                bookmark_hash = bookmark.get('hash')
                if bookmark_hash and bookmark_hash not in seen_hashes:
                    seen_hashes.add(bookmark_hash)
                    new_bookmarks.append(bookmark)
            
            print(f"  📊 Got {len(bookmarks)} bookmarks, {len(new_bookmarks)} are new")
            
            if not new_bookmarks:
                print(f"  ✅ No new bookmarks in this batch - we have everything!")
                break
            
            all_bookmarks.extend(new_bookmarks)
            print(f"  📈 Total unique bookmarks now: {len(all_bookmarks)}")
            
            # Rate limiting
            sleep(1)
            
            # Safety check - if we get more than 10,000, something might be wrong
            if len(all_bookmarks) > 10000:
                print(f"⚠️ Retrieved {len(all_bookmarks)} bookmarks - stopping for safety")
                break
                
        except Exception as e:
            print(f"❌ Error in batch {batch_count}: {e}")
            break
    
    print(f"🎉 Final total: {len(all_bookmarks)} unique bookmarks")
    return all_bookmarks

def save_unlimited_backup(bookmarks):
    """Save the complete unlimited backup"""
    
    if not bookmarks:
        print("❌ No bookmarks to save")
        return
    
    timestamp = "2025-08-05-unlimited"
    
    # Create backup directory
    os.makedirs("backups", exist_ok=True)
    
    # Save complete JSON backup
    json_file = f"instapaper_unlimited_backup_{timestamp}.json"
    json_path = os.path.join("backups", json_file)
    
    backup_data = {
        'export_date': timestamp,
        'total_bookmarks': len(bookmarks),
        'retrieval_method': 'hash-based_pagination',
        'bookmarks': bookmarks
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Complete backup saved to: {json_path}")
    
    # Create a simple CSV for easy viewing
    csv_file = f"instapaper_unlimited_list_{timestamp}.csv"
    csv_path = os.path.join("backups", csv_file)
    
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("title,url,time,starred,hash\n")
        for bookmark in bookmarks:
            title = (bookmark.get('title', '') or '').replace('"', '""')
            url = bookmark.get('url', '')
            time = bookmark.get('time', '')
            starred = bookmark.get('starred', 0)
            hash_val = bookmark.get('hash', '')
            f.write(f'"{title}","{url}",{time},{starred},{hash_val}\n')
    
    print(f"📊 CSV list saved to: {csv_path}")
    
    # Create summary
    summary_file = f"instapaper_unlimited_summary_{timestamp}.txt"
    summary_path = os.path.join("backups", summary_file)
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Instapaper Unlimited Backup Summary\n")
        f.write(f"===================================\n")
        f.write(f"Export Date: {timestamp}\n")
        f.write(f"Total Bookmarks: {len(bookmarks):,}\n")
        f.write(f"Retrieval Method: Hash-based pagination\n\n")
        
        # Count by starred status
        starred_count = sum(1 for b in bookmarks if b.get('starred'))
        f.write(f"Starred bookmarks: {starred_count}\n")
        f.write(f"Regular bookmarks: {len(bookmarks) - starred_count}\n\n")
        
        # Sample titles
        f.write("Sample bookmark titles:\n")
        for i, bookmark in enumerate(bookmarks[:20]):
            title = bookmark.get('title', 'No title')[:80]
            f.write(f"  {i+1:2d}. {title}\n")
        
        if len(bookmarks) > 20:
            f.write(f"  ... and {len(bookmarks) - 20:,} more\n")
    
    print(f"📋 Summary saved to: {summary_path}")

if __name__ == '__main__':
    print("🚀 Starting UNLIMITED Instapaper backup...")
    print("   Using hash-based pagination to get ALL bookmarks")
    print()
    
    bookmarks = get_all_bookmarks_unlimited()
    
    if bookmarks:
        save_unlimited_backup(bookmarks)
        print(f"\n✅ SUCCESS! Retrieved {len(bookmarks):,} total bookmarks")
        print("   This should be much closer to your actual collection size!")
    else:
        print("❌ No bookmarks retrieved - check credentials or connection")