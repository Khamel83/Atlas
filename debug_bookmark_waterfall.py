#!/usr/bin/env python3
"""
Debug the bookmark waterfall to find where we're losing 800-900 bookmarks
"""

import json
import os

def debug_bookmark_waterfall():
    """Trace exactly where bookmarks are being lost in the process"""
    
    backup_file = "backups/instapaper_complete_extraction_2025-08-05-complete.json"
    
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return
    
    print("🔍 BOOKMARK WATERFALL ANALYSIS")
    print("=" * 60)
    
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    print(f"📊 Raw backup data:")
    print(f"  - Total bookmarks reported: {backup_data.get('total_bookmarks', 'Unknown')}")
    print(f"  - Total folders: {backup_data.get('total_folders', 'Unknown')}")
    print()
    
    folders = backup_data.get('folders', {})
    
    # Step 1: Count raw bookmarks in each folder
    print("📁 STEP 1: Raw bookmark counts per folder")
    print("-" * 40)
    
    total_raw_bookmarks = 0
    folder_details = {}
    
    for folder_name, folder_data in folders.items():
        if isinstance(folder_data, dict) and 'bookmarks' in folder_data:
            bookmark_count = folder_data.get('bookmark_count', 0)
            actual_bookmarks = len(folder_data.get('bookmarks', []))
            
            folder_details[folder_name] = {
                'reported_count': bookmark_count,
                'actual_count': actual_bookmarks,
                'bookmarks': folder_data.get('bookmarks', [])
            }
            
            total_raw_bookmarks += actual_bookmarks
            
            print(f"  {folder_name:15} | Reported: {bookmark_count:4d} | Actual: {actual_bookmarks:4d}")
    
    print(f"  {'TOTAL':15} | Raw bookmarks: {total_raw_bookmarks:4d}")
    print()
    
    # Step 2: Check for duplicates within folders
    print("🔍 STEP 2: Duplicate analysis within folders")
    print("-" * 40)
    
    for folder_name, details in folder_details.items():
        bookmarks = details['bookmarks']
        bookmark_ids = [str(b.get('bookmark_id', '')) for b in bookmarks if b.get('bookmark_id')]
        unique_ids = set(bookmark_ids)
        
        duplicates_within = len(bookmark_ids) - len(unique_ids)
        
        print(f"  {folder_name:15} | Total: {len(bookmarks):4d} | Unique IDs: {len(unique_ids):4d} | Duplicates: {duplicates_within:4d}")
        
        # Show sample bookmark IDs for inspection
        if bookmark_ids:
            print(f"    Sample IDs: {bookmark_ids[:3]}")
        
        # Check for bookmarks without IDs
        no_id_count = sum(1 for b in bookmarks if not b.get('bookmark_id'))
        if no_id_count > 0:
            print(f"    ⚠️  Bookmarks without IDs: {no_id_count}")
    
    print()
    
    # Step 3: Cross-folder deduplication simulation
    print("🔗 STEP 3: Cross-folder deduplication simulation")
    print("-" * 40)
    
    all_bookmark_ids = set()
    all_bookmarks_with_context = {}
    folder_membership = {}
    
    for folder_name, details in folder_details.items():
        folder_id = folders[folder_name].get('folder_id', folder_name)
        folder_type = folders[folder_name].get('folder_type', 'unknown')
        
        bookmarks = details['bookmarks']
        
        for bookmark in bookmarks:
            bookmark_id = str(bookmark.get('bookmark_id', ''))
            
            if bookmark_id and bookmark_id != '':
                all_bookmark_ids.add(bookmark_id)
                
                # Track which folders each bookmark appears in
                if bookmark_id not in folder_membership:
                    folder_membership[bookmark_id] = []
                    all_bookmarks_with_context[bookmark_id] = bookmark
                
                folder_membership[bookmark_id].append({
                    'folder_id': folder_id,
                    'folder_title': folder_name,
                    'folder_type': folder_type
                })
    
    print(f"  Total unique bookmark IDs across all folders: {len(all_bookmark_ids)}")
    print(f"  Bookmarks with folder context: {len(all_bookmarks_with_context)}")
    print()
    
    # Step 4: Multi-folder membership analysis
    print("📊 STEP 4: Multi-folder membership analysis")
    print("-" * 40)
    
    single_folder = 0
    multi_folder = 0
    folder_counts = {}
    
    for bookmark_id, folders_list in folder_membership.items():
        folder_count = len(folders_list)
        
        if folder_count == 1:
            single_folder += 1
        else:
            multi_folder += 1
        
        folder_counts[folder_count] = folder_counts.get(folder_count, 0) + 1
    
    print(f"  Single folder bookmarks: {single_folder}")
    print(f"  Multi-folder bookmarks: {multi_folder}")
    print(f"  Folder membership distribution:")
    
    for count, num_bookmarks in sorted(folder_counts.items()):
        print(f"    In {count} folder(s): {num_bookmarks} bookmarks")
    
    print()
    
    # Step 5: Sample inspection
    print("🔍 STEP 5: Sample bookmark inspection")
    print("-" * 40)
    
    # Show a few multi-folder bookmarks
    multi_folder_samples = [(bid, folders) for bid, folders in folder_membership.items() if len(folders) > 1][:5]
    
    for bookmark_id, folders_list in multi_folder_samples:
        folder_names = [f['folder_title'] for f in folders_list]
        bookmark_data = all_bookmarks_with_context[bookmark_id]
        title = bookmark_data.get('title', 'No title')[:50]
        
        print(f"  ID {bookmark_id}: '{title}'")
        print(f"    Appears in: {', '.join(folder_names)}")
        print()
    
    # Step 6: Final calculation
    print("🎯 STEP 6: Final calculation")
    print("-" * 40)
    
    expected_files = len(all_bookmarks_with_context)
    actual_html_files = len([f for f in os.listdir('output/articles/html') if f.endswith('.html')]) if os.path.exists('output/articles/html') else 0
    
    print(f"  Expected files based on unique bookmarks: {expected_files}")
    print(f"  Actual HTML files created: {actual_html_files}")
    print(f"  Difference: {expected_files - actual_html_files}")
    
    if expected_files != actual_html_files:
        print(f"  ⚠️  MISMATCH DETECTED!")
    else:
        print(f"  ✅ Counts match!")
    
    # Step 7: Check for processing issues
    print()
    print("🔧 STEP 7: Processing issues check")
    print("-" * 40)
    
    # Check for bookmarks without essential data
    problematic_bookmarks = 0
    for bookmark_id, bookmark_data in all_bookmarks_with_context.items():
        title = bookmark_data.get('title', '')
        url = bookmark_data.get('url', '')
        
        if not title and not url:
            problematic_bookmarks += 1
    
    print(f"  Bookmarks without title or URL: {problematic_bookmarks}")
    
    # Summary
    print()
    print("📋 WATERFALL SUMMARY")
    print("=" * 60)
    print(f"  Raw bookmarks in backup: {total_raw_bookmarks}")
    print(f"  After deduplication: {len(all_bookmarks_with_context)}")
    print(f"  Files created: {actual_html_files}")
    print(f"  Missing files: {len(all_bookmarks_with_context) - actual_html_files}")

if __name__ == '__main__':
    debug_bookmark_waterfall()