#!/usr/bin/env python3
"""
Complete Instapaper extraction using proper bookmark ID pagination
"""

import json
import os
from time import sleep
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def get_complete_instapaper_data():
    """Get ALL bookmarks from ALL folders using proper bookmark ID pagination"""
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')  
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return {}
    
    print("✅ Authentication successful")
    print("=" * 60)
    
    # Get folder structure
    folders = get_folders(client)
    
    # Add default folders (unread, archive, starred)
    default_folders = [
        {'folder_id': 'unread', 'title': 'Unread', 'type': 'default'},
        {'folder_id': 'archive', 'title': 'Archive', 'type': 'default'}, 
        {'folder_id': 'starred', 'title': 'Starred', 'type': 'default'}
    ]
    
    all_folders = default_folders + folders
    
    print(f"📁 Found {len(all_folders)} folders to process:")
    for folder in all_folders:
        print(f"  - {folder.get('title')} (ID: {folder.get('folder_id')})")
    
    print()
    
    # Extract from each folder
    all_results = {}
    total_bookmarks = 0
    
    for folder in all_folders:
        folder_id = folder.get('folder_id')
        folder_title = folder.get('title')
        folder_type = folder.get('type', 'custom')
        
        print(f"📁 Processing folder: {folder_title}")
        
        bookmarks = extract_folder_completely(client, folder_id, folder_type)
        
        if bookmarks:
            all_results[folder_title] = {
                'folder_id': folder_id,
                'folder_type': folder_type,
                'bookmark_count': len(bookmarks), 
                'bookmarks': bookmarks
            }
            total_bookmarks += len(bookmarks)
            print(f"  ✅ Extracted {len(bookmarks)} bookmarks")
        else:
            print(f"  ⚠️ No bookmarks found")
        
        sleep(1)  # Rate limiting
    
    print(f"\n🎉 TOTAL EXTRACTION COMPLETE: {total_bookmarks} bookmarks across {len(all_results)} folders")
    return all_results

def get_folders(client):
    """Get custom folder list"""
    
    url = client.BASE_URL + "folders/list"
    
    try:
        response = client.oauth.post(url)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list):
            return [item for item in data if item.get('type') == 'folder']
        
    except Exception as e:
        print(f"⚠️ Error getting folders: {e}")
    
    return []

def extract_folder_completely(client, folder_id, folder_type):
    """Extract ALL bookmarks from a single folder using proper pagination"""
    
    all_bookmarks = []
    seen_bookmark_ids = set()
    batch_count = 0
    
    while True:
        batch_count += 1
        print(f"  📥 Batch {batch_count} (have {len(seen_bookmark_ids)} IDs)...")
        
        # Prepare parameters
        params = {'limit': 500}
        
        # Use appropriate folder parameter based on type
        if folder_type == 'default':
            params['folder'] = folder_id  # "unread", "archive", "starred"
        else:
            params['folder_id'] = folder_id  # Numeric ID for custom folders
        
        # Add 'have' parameter with bookmark IDs we've already seen
        if seen_bookmark_ids:
            params['have'] = ','.join(map(str, sorted(seen_bookmark_ids)))
        
        try:
            url = client.BASE_URL + "bookmarks/list"
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                print(f"    ⚠️ Unexpected response format")
                break
            
            # Extract bookmarks
            bookmarks = [item for item in data if item.get('type') == 'bookmark']
            
            if not bookmarks:
                print(f"    ✅ No more bookmarks in this folder")
                break
            
            # Find truly new bookmarks
            new_bookmarks = []
            for bookmark in bookmarks:
                bookmark_id = bookmark.get('bookmark_id')
                if bookmark_id and bookmark_id not in seen_bookmark_ids:
                    seen_bookmark_ids.add(bookmark_id)
                    new_bookmarks.append(bookmark)
            
            if not new_bookmarks:
                print(f"    ✅ No new bookmarks in this batch - complete!")
                break
            
            all_bookmarks.extend(new_bookmarks)
            print(f"    📊 Got {len(new_bookmarks)} new bookmarks (total: {len(all_bookmarks)})")
            
            sleep(0.5)  # Rate limiting
            
            # Safety check
            if len(all_bookmarks) > 20000:
                print(f"    ⚠️ Safety limit reached at {len(all_bookmarks)} bookmarks")
                break
                
        except Exception as e:
            print(f"    ❌ Error in batch {batch_count}: {e}")
            break
    
    return all_bookmarks

def save_complete_extraction(results):
    """Save the complete extraction results"""
    
    if not results:
        print("❌ No results to save")
        return
    
    timestamp = "2025-08-05-complete"
    os.makedirs("backups", exist_ok=True)
    
    # Calculate totals
    total_bookmarks = sum(folder_data['bookmark_count'] for folder_data in results.values())
    
    # Save comprehensive JSON
    json_file = f"instapaper_complete_extraction_{timestamp}.json"
    json_path = os.path.join("backups", json_file)
    
    export_data = {
        'export_timestamp': timestamp,
        'total_bookmarks': total_bookmarks,
        'total_folders': len(results),
        'extraction_method': 'bookmark_id_pagination',
        'folders': results
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Complete extraction saved to: {json_path}")
    
    # Create summary report
    summary_file = f"instapaper_extraction_report_{timestamp}.txt"
    summary_path = os.path.join("backups", summary_file)
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("INSTAPAPER COMPLETE EXTRACTION REPORT\n")
        f.write("====================================\n\n")
        f.write(f"Export Timestamp: {timestamp}\n")
        f.write(f"Total Bookmarks: {total_bookmarks:,}\n")
        f.write(f"Total Folders: {len(results)}\n\n")
        
        f.write("FOLDER BREAKDOWN:\n")
        f.write("-" * 50 + "\n")
        
        for folder_name, folder_data in results.items():
            count = folder_data['bookmark_count']
            folder_id = folder_data['folder_id']
            f.write(f"{folder_name:20} | {count:6,} bookmarks | ID: {folder_id}\n")
        
        f.write("-" * 50 + "\n")
        f.write(f"{'TOTAL':20} | {total_bookmarks:6,} bookmarks\n\n")
        
        # Sample titles from each folder
        f.write("SAMPLE TITLES BY FOLDER:\n")
        f.write("=" * 50 + "\n")
        
        for folder_name, folder_data in results.items():
            f.write(f"\n{folder_name} ({folder_data['bookmark_count']} total):\n")
            bookmarks = folder_data['bookmarks'][:5]  # First 5
            for i, bookmark in enumerate(bookmarks):
                title = bookmark.get('title', 'No title')[:60]
                f.write(f"  {i+1}. {title}\n")
            if folder_data['bookmark_count'] > 5:
                f.write(f"  ... and {folder_data['bookmark_count'] - 5} more\n")
    
    print(f"📊 Extraction report saved to: {summary_path}")

if __name__ == '__main__':
    print("🚀 COMPLETE INSTAPAPER EXTRACTION")
    print("📁 Getting ALL bookmarks from ALL folders using proper pagination")
    print("🎯 This should finally get your thousands of bookmarks!")
    print()
    
    results = get_complete_instapaper_data()
    
    if results:
        save_complete_extraction(results)
        
        total = sum(folder_data['bookmark_count'] for folder_data in results.values())
        print(f"\n✅ SUCCESS! Extracted {total:,} total bookmarks")
        print("📋 This should be much closer to your CSV count of ~56K!")
    else:
        print("❌ Extraction failed")