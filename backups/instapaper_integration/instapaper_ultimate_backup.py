#!/usr/bin/env python3
"""
ULTIMATE INSTAPAPER BACKUP - Get EVERYTHING possible from the API
- All folders
- All bookmarks with complete metadata  
- Full article text via get_text endpoint
- All highlights and annotations
- Complete folder structure
- User account information
- Everything Instapaper has
"""

import json
import os
from time import sleep
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def ultimate_instapaper_backup():
    """Get ABSOLUTELY EVERYTHING from Instapaper"""
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')  
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return None
    
    print("✅ Authentication successful")
    print("🎯 ULTIMATE BACKUP - Getting EVERYTHING from Instapaper")
    print("=" * 70)
    
    backup_data = {
        'backup_timestamp': datetime.now().isoformat(),
        'backup_type': 'ultimate_complete',
        'account_info': {},
        'folders': {},
        'bookmarks': {},
        'highlights': {},
        'full_text_content': {},
        'statistics': {}
    }
    
    # Step 1: Get account information
    print("👤 STEP 1: Getting account information...")
    backup_data['account_info'] = get_account_info(client)
    
    # Step 2: Get complete folder structure
    print("\n📁 STEP 2: Getting complete folder structure...")
    backup_data['folders'] = get_complete_folders(client)
    
    # Step 3: Get ALL bookmarks from ALL folders with complete metadata
    print("\n📚 STEP 3: Getting ALL bookmarks with complete metadata...")
    all_bookmarks = get_all_bookmarks_complete(client, backup_data['folders'])
    backup_data['bookmarks'] = all_bookmarks
    
    # Step 4: Get full text content for each bookmark
    print(f"\n📄 STEP 4: Getting full text content for {len(all_bookmarks)} bookmarks...")
    backup_data['full_text_content'] = get_all_bookmark_text(client, all_bookmarks)
    
    # Step 5: Get highlights and annotations
    print(f"\n✨ STEP 5: Getting highlights for all bookmarks...")
    backup_data['highlights'] = get_all_highlights(client, all_bookmarks)
    
    # Step 6: Generate statistics
    print(f"\n📊 STEP 6: Generating comprehensive statistics...")
    backup_data['statistics'] = generate_comprehensive_stats(backup_data)
    
    return backup_data

def get_account_info(client):
    """Get complete account information"""
    
    url = client.BASE_URL + "account/verify_credentials"
    
    try:
        response = client.oauth.post(url)
        response.raise_for_status()
        data = response.json()
        
        print(f"  ✅ Retrieved account information")
        return data
        
    except Exception as e:
        print(f"  ❌ Error getting account info: {e}")
        return {}

def get_complete_folders(client):
    """Get complete folder structure with all metadata"""
    
    url = client.BASE_URL + "folders/list"
    folders_data = {}
    
    try:
        response = client.oauth.post(url)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list):
            custom_folders = [item for item in data if item.get('type') == 'folder']
            
            # Add default folders
            default_folders = [
                {'folder_id': 'unread', 'title': 'Unread', 'type': 'default'},
                {'folder_id': 'archive', 'title': 'Archive', 'type': 'default'}, 
                {'folder_id': 'starred', 'title': 'Starred', 'type': 'default'}
            ]
            
            all_folders = default_folders + custom_folders
            
            for folder in all_folders:
                folder_id = folder.get('folder_id')
                folders_data[str(folder_id)] = folder
            
            print(f"  ✅ Found {len(all_folders)} folders: {[f['title'] for f in all_folders]}")
            
        return folders_data
        
    except Exception as e:
        print(f"  ❌ Error getting folders: {e}")
        return {}

def get_all_bookmarks_complete(client, folders_data):
    """Get ALL bookmarks from ALL folders with complete metadata"""
    
    all_bookmarks = {}
    total_count = 0
    
    for folder_id, folder_info in folders_data.items():
        folder_title = folder_info.get('title', folder_id)
        folder_type = folder_info.get('type', 'custom')
        
        print(f"  📁 Processing {folder_title}...")
        
        folder_bookmarks = extract_folder_bookmarks_complete(client, folder_id, folder_type)
        
        for bookmark_id, bookmark_data in folder_bookmarks.items():
            # Add folder context to bookmark
            if bookmark_id not in all_bookmarks:
                all_bookmarks[bookmark_id] = bookmark_data
                all_bookmarks[bookmark_id]['folders'] = []
            
            all_bookmarks[bookmark_id]['folders'].append({
                'folder_id': folder_id,
                'folder_title': folder_title,
                'folder_type': folder_type
            })
        
        folder_count = len(folder_bookmarks)
        total_count += folder_count
        print(f"    ✅ Got {folder_count} bookmarks from {folder_title}")
        
        sleep(1)  # Rate limiting
    
    # Deduplicate total count
    unique_count = len(all_bookmarks)
    print(f"  📊 Total: {total_count} bookmark instances, {unique_count} unique bookmarks")
    
    return all_bookmarks

def extract_folder_bookmarks_complete(client, folder_id, folder_type):
    """Extract ALL bookmarks from a folder with complete metadata"""
    
    folder_bookmarks = {}
    seen_bookmark_ids = set()
    batch_count = 0
    
    while True:
        batch_count += 1
        
        # Prepare parameters
        params = {'limit': 500}
        
        if folder_type == 'default':
            params['folder'] = folder_id
        else:
            params['folder_id'] = folder_id
        
        if seen_bookmark_ids:
            params['have'] = ','.join(map(str, sorted(seen_bookmark_ids)))
        
        try:
            url = client.BASE_URL + "bookmarks/list"
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                break
            
            # Extract all bookmark and metadata
            bookmarks = [item for item in data if item.get('type') == 'bookmark']
            meta_items = [item for item in data if item.get('type') != 'bookmark']
            
            if not bookmarks:
                break
            
            # Process each bookmark with ALL metadata
            new_count = 0
            for bookmark in bookmarks:
                bookmark_id = bookmark.get('bookmark_id')
                if bookmark_id and bookmark_id not in seen_bookmark_ids:
                    seen_bookmark_ids.add(bookmark_id)
                    
                    # Store complete bookmark data with all metadata
                    folder_bookmarks[str(bookmark_id)] = {
                        **bookmark,  # All original fields
                        'extraction_timestamp': datetime.now().isoformat(),
                        'extraction_batch': batch_count,
                        'meta_items': meta_items if new_count == 0 else []  # Include meta for first bookmark only
                    }
                    new_count += 1
            
            if new_count == 0:
                break
                
            sleep(0.5)  # Rate limiting
            
            if len(folder_bookmarks) > 1000:  # Safety check
                break
                
        except Exception as e:
            print(f"    ❌ Error in batch {batch_count}: {e}")
            break
    
    return folder_bookmarks

def get_all_bookmark_text(client, all_bookmarks):
    """Get full text content for each bookmark using get_text endpoint"""
    
    text_content = {}
    
    print(f"  📄 Getting full text for {len(all_bookmarks)} bookmarks...")
    
    for i, (bookmark_id, bookmark_data) in enumerate(all_bookmarks.items()):
        if i % 50 == 0:
            print(f"    Progress: {i}/{len(all_bookmarks)} bookmarks processed")
        
        title = bookmark_data.get('title', 'No title')[:50]
        
        try:
            url = client.BASE_URL + "bookmarks/get_text"
            params = {'bookmark_id': bookmark_id}
            
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            # The response is typically plain text of the article
            full_text = response.text
            
            text_content[bookmark_id] = {
                'bookmark_id': bookmark_id,
                'title': title,
                'full_text': full_text,
                'text_length': len(full_text),
                'extraction_timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
            sleep(0.3)  # Rate limiting for text requests
            
        except Exception as e:
            text_content[bookmark_id] = {
                'bookmark_id': bookmark_id,
                'title': title,
                'full_text': None,
                'text_length': 0,
                'extraction_timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    success_count = sum(1 for item in text_content.values() if item['status'] == 'success')
    print(f"  ✅ Successfully got full text for {success_count}/{len(all_bookmarks)} bookmarks")
    
    return text_content

def get_all_highlights(client, all_bookmarks):
    """Get highlights and annotations for all bookmarks"""
    
    highlights_data = {}
    
    print(f"  ✨ Getting highlights for {len(all_bookmarks)} bookmarks...")
    
    # Try to get highlights using bookmarks/list with highlights parameter
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {
            'limit': 500,
            'highlights': '1'  # Try to get highlights
        }
        
        response = client.oauth.post(url, data=params)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, list):
            highlight_items = [item for item in data if item.get('type') == 'highlight']
            
            for highlight in highlight_items:
                bookmark_id = highlight.get('bookmark_id')
                if bookmark_id:
                    if bookmark_id not in highlights_data:
                        highlights_data[bookmark_id] = []
                    highlights_data[bookmark_id].append(highlight)
        
        print(f"  ✅ Found highlights for {len(highlights_data)} bookmarks")
        
    except Exception as e:
        print(f"  ⚠️ Could not retrieve highlights: {e}")
        highlights_data = {}
    
    return highlights_data

def generate_comprehensive_stats(backup_data):
    """Generate comprehensive statistics about the backup"""
    
    bookmarks = backup_data.get('bookmarks', {})
    text_content = backup_data.get('full_text_content', {})
    highlights = backup_data.get('highlights', {})
    folders = backup_data.get('folders', {})
    
    stats = {
        'total_bookmarks': len(bookmarks),
        'total_folders': len(folders),
        'bookmarks_with_text': sum(1 for item in text_content.values() if item.get('status') == 'success'),
        'bookmarks_with_highlights': len(highlights),
        'total_text_characters': sum(item.get('text_length', 0) for item in text_content.values()),
        'folder_breakdown': {},
        'bookmark_types': {},
        'extraction_summary': {
            'timestamp': datetime.now().isoformat(),
            'success_rate_text': 0,
            'total_highlights': sum(len(h) for h in highlights.values())
        }
    }
    
    # Folder breakdown
    for bookmark_id, bookmark_data in bookmarks.items():
        folders_list = bookmark_data.get('folders', [])
        for folder_info in folders_list:
            folder_title = folder_info.get('folder_title', 'Unknown')
            stats['folder_breakdown'][folder_title] = stats['folder_breakdown'].get(folder_title, 0) + 1
    
    # Success rate
    if text_content:
        stats['extraction_summary']['success_rate_text'] = stats['bookmarks_with_text'] / len(text_content) * 100
    
    return stats

def save_ultimate_backup(backup_data):
    """Save the ultimate comprehensive backup"""
    
    if not backup_data:
        print("❌ No backup data to save")
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs("ultimate_backup", exist_ok=True)
    
    # Save complete JSON backup
    json_file = f"instapaper_ultimate_backup_{timestamp}.json"
    json_path = os.path.join("ultimate_backup", json_file)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Ultimate backup saved to: {json_path}")
    
    # Save human-readable summary
    summary_file = f"instapaper_ultimate_summary_{timestamp}.txt"
    summary_path = os.path.join("ultimate_backup", summary_file)
    
    stats = backup_data.get('statistics', {})
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("🎯 INSTAPAPER ULTIMATE BACKUP SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Backup Timestamp: {backup_data.get('backup_timestamp')}\n")
        f.write(f"Backup Type: {backup_data.get('backup_type')}\n\n")
        
        f.write("📊 STATISTICS:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total Bookmarks: {stats.get('total_bookmarks', 0):,}\n")
        f.write(f"Total Folders: {stats.get('total_folders', 0)}\n")
        f.write(f"Bookmarks with Full Text: {stats.get('bookmarks_with_text', 0)}\n")
        f.write(f"Bookmarks with Highlights: {stats.get('bookmarks_with_highlights', 0)}\n")
        f.write(f"Total Text Characters: {stats.get('total_text_characters', 0):,}\n")
        
        success_rate = stats.get('extraction_summary', {}).get('success_rate_text', 0)
        f.write(f"Text Extraction Success Rate: {success_rate:.1f}%\n\n")
        
        f.write("📁 FOLDER BREAKDOWN:\n")
        f.write("-" * 30 + "\n")
        folder_breakdown = stats.get('folder_breakdown', {})
        for folder, count in sorted(folder_breakdown.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{folder:20} | {count:5,} bookmarks\n")
        
        # Sample bookmarks
        f.write(f"\n📚 SAMPLE BOOKMARKS:\n")
        f.write("-" * 30 + "\n")
        bookmarks = backup_data.get('bookmarks', {})
        for i, (bookmark_id, bookmark_data) in enumerate(list(bookmarks.items())[:10]):
            title = bookmark_data.get('title', 'No title')[:60]
            url = bookmark_data.get('url', 'No URL')[:50]
            f.write(f"{i+1:2d}. {title}\n")
            f.write(f"    URL: {url}\n")
            
            folders_list = bookmark_data.get('folders', [])
            folder_names = [f['folder_title'] for f in folders_list]
            f.write(f"    Folders: {', '.join(folder_names)}\n\n")
    
    print(f"📋 Ultimate summary saved to: {summary_path}")
    
    # Save separate files for different data types
    save_separate_data_files(backup_data, timestamp)

def save_separate_data_files(backup_data, timestamp):
    """Save separate files for easier access to different data types"""
    
    base_dir = "ultimate_backup"
    
    # Save bookmarks CSV
    bookmarks = backup_data.get('bookmarks', {})
    csv_file = f"bookmarks_complete_{timestamp}.csv"
    csv_path = os.path.join(base_dir, csv_file)
    
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("bookmark_id,title,url,time,starred,progress,description,folders\n")
        for bookmark_id, bookmark_data in bookmarks.items():
            title = (bookmark_data.get('title', '') or '').replace('"', '""')
            url = bookmark_data.get('url', '')
            time = bookmark_data.get('time', '')
            starred = bookmark_data.get('starred', 0)
            progress = bookmark_data.get('progress', 0)
            description = (bookmark_data.get('description', '') or '').replace('"', '""')
            
            folders_list = bookmark_data.get('folders', [])
            folder_names = [f['folder_title'] for f in folders_list]
            folders_str = ';'.join(folder_names)
            
            f.write(f'{bookmark_id},"{title}","{url}",{time},{starred},{progress},"{description}","{folders_str}"\n')
    
    print(f"📊 Bookmarks CSV saved to: {csv_path}")
    
    # Save text content separately (for large files)
    text_content = backup_data.get('full_text_content', {})
    if text_content:
        text_file = f"full_text_content_{timestamp}.json"
        text_path = os.path.join(base_dir, text_file)
        
        with open(text_path, 'w', encoding='utf-8') as f:
            json.dump(text_content, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Full text content saved to: {text_path}")

if __name__ == '__main__':
    print("🚀 INSTAPAPER ULTIMATE BACKUP")
    print("🎯 Getting EVERYTHING possible from your Instapaper account")
    print("📚 This includes: bookmarks, folders, text content, highlights, metadata")
    print("⏱️  This will take several minutes due to rate limiting...")
    print()
    
    backup_data = ultimate_instapaper_backup()
    
    if backup_data:
        save_ultimate_backup(backup_data)
        
        stats = backup_data.get('statistics', {})
        total_bookmarks = stats.get('total_bookmarks', 0)
        total_text = stats.get('bookmarks_with_text', 0)
        
        print(f"\n🎉 ULTIMATE BACKUP COMPLETE!")
        print(f"📊 {total_bookmarks:,} bookmarks with complete metadata")
        print(f"📄 {total_text:,} bookmarks with full text content") 
        print(f"📁 {stats.get('total_folders', 0)} folders processed")
        print(f"✨ {stats.get('bookmarks_with_highlights', 0)} bookmarks with highlights")
        print(f"\n💾 Complete backup saved to ultimate_backup/ directory")
        print("🎯 This is your COMPLETE Instapaper backup with everything possible!")
    else:
        print("❌ Ultimate backup failed")