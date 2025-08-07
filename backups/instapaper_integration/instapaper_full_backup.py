#!/usr/bin/env python3
"""
Complete Instapaper backup script - gets ALL bookmarks from ALL folders
"""

import json
import os
from time import sleep
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def get_all_bookmarks():
    """Get ALL bookmarks from ALL folders with proper pagination"""
    
    # OAuth credentials from .env
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')  
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing credentials in .env file")
        return []
    
    # Initialize client
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return []
    
    print("✅ Authentication successful")
    
    # Folders to check - get ALL bookmarks
    folders_to_check = ["unread", "archive", "starred"]
    all_bookmarks = []
    seen_bookmark_ids = set()
    
    for folder in folders_to_check:
        print(f"📁 Fetching from folder: {folder}")
        folder_bookmarks = get_folder_bookmarks(client, folder)
        
        # Deduplicate by bookmark_id
        new_bookmarks = []
        for bookmark in folder_bookmarks:
            bookmark_id = bookmark.get('bookmark_id')
            if bookmark_id and bookmark_id not in seen_bookmark_ids:
                seen_bookmark_ids.add(bookmark_id)
                new_bookmarks.append(bookmark)
        
        print(f"📊 Found {len(new_bookmarks)} unique bookmarks in {folder}")
        all_bookmarks.extend(new_bookmarks)
        
        sleep(1)  # Be nice to API
    
    print(f"🎉 Total unique bookmarks: {len(all_bookmarks)}")
    return all_bookmarks

def get_folder_bookmarks(client, folder):
    """Get all bookmarks from a specific folder with proper pagination"""
    
    all_bookmarks = []
    have_ids = []  # Track what we've seen for pagination
    
    while True:
        # Prepare request params
        params = {
            'limit': 500,  # Max allowed
            'folder': folder
        }
        
        # Add pagination parameter
        if have_ids:
            params['have'] = ','.join(map(str, have_ids))
        
        # Make API call with proper parameters
        print(f"  📥 Fetching batch (have {len(have_ids)} seen)...")
        
        try:
            # Manual API call since we need custom params
            url = client.BASE_URL + "bookmarks/list"
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                print(f"  ⚠️ Unexpected response format: {type(data)}")
                break
                
            # Filter out metadata entries and get actual bookmarks
            bookmarks = [item for item in data if item.get('type') == 'bookmark']
            
            if not bookmarks:
                print(f"  ✅ No more bookmarks in {folder}")
                break
            
            print(f"  📊 Got {len(bookmarks)} bookmarks in this batch")
            all_bookmarks.extend(bookmarks)
            
            # Update have_ids for next iteration
            for bookmark in bookmarks:
                bookmark_id = bookmark.get('bookmark_id')
                if bookmark_id:
                    have_ids.append(bookmark_id)
                    
            sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"  ❌ Error fetching from {folder}: {e}")
            break
    
    return all_bookmarks

def save_backup(bookmarks):
    """Save complete backup to JSON file"""
    
    timestamp = "2025-08-05"
    filename = f"instapaper_complete_backup_{timestamp}.json"
    
    # Create backup directory
    os.makedirs("backups", exist_ok=True)
    filepath = os.path.join("backups", filename)
    
    # Save raw backup
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'total_bookmarks': len(bookmarks),
            'export_date': timestamp,
            'folders_included': ['unread', 'archive', 'starred'],
            'bookmarks': bookmarks
        }, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Complete backup saved to: {filepath}")
    
    # Save summary stats
    summary_file = f"instapaper_backup_summary_{timestamp}.txt"
    summary_path = os.path.join("backups", summary_file)
    
    with open(summary_path, 'w') as f:
        f.write(f"Instapaper Backup Summary\n")
        f.write(f"========================\n")
        f.write(f"Export Date: {timestamp}\n")
        f.write(f"Total Bookmarks: {len(bookmarks)}\n\n")
        
        # Folder breakdown
        folder_counts = {}
        for bookmark in bookmarks:
            folder = bookmark.get('folder', 'unknown')
            folder_counts[folder] = folder_counts.get(folder, 0) + 1
        
        f.write("Breakdown by Folder:\n")
        for folder, count in folder_counts.items():
            f.write(f"  {folder}: {count}\n")
        
        f.write(f"\nFirst 10 bookmark titles:\n")
        for i, bookmark in enumerate(bookmarks[:10]):
            title = bookmark.get('title', 'No title')[:60]
            f.write(f"  {i+1}. {title}\n")
    
    print(f"📋 Summary saved to: {summary_path}")

if __name__ == '__main__':
    print("🚀 Starting complete Instapaper backup...")
    
    bookmarks = get_all_bookmarks()
    
    if bookmarks:
        save_backup(bookmarks)
        print(f"✅ Backup complete! Retrieved {len(bookmarks)} total bookmarks")
    else:
        print("❌ No bookmarks retrieved - check credentials or connection")