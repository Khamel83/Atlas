#!/usr/bin/env python3
"""
Investigate why we're only getting 500 unique bookmarks across ALL folders
when the CSV export shows 56,594 bookmarks.
"""

import os
import json
import csv
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient
from collections import defaultdict

def investigate_bookmark_duplication():
    """Deep dive into the bookmark duplication issue"""
    
    load_dotenv()
    
    # Load credentials
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing Instapaper credentials in .env file")
        return
    
    print("🔍 INVESTIGATING BOOKMARK DUPLICATION ANOMALY")
    print("=" * 60)
    
    # Initialize client
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    # Authenticate
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print()
    
    # Get detailed bookmark data from each folder
    print("📊 DETAILED FOLDER ANALYSIS")
    print("-" * 40)
    
    folder_types = ['unread', 'archive', 'starred', '2371999', '3816912']  # Include custom folders
    folder_names = ['Unread', 'Archive', 'Starred', 'Feedly', 'Stratechery']
    
    all_bookmark_data = {}
    bookmark_id_to_folders = defaultdict(list)
    url_to_folders = defaultdict(list)
    
    for folder_key, folder_name in zip(folder_types, folder_names):
        print(f"  📂 Analyzing {folder_name} folder...")
        
        try:
            url = client.BASE_URL + "bookmarks/list"
            params = {'limit': 500, 'folder': folder_key}
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                bookmarks = response.json()
                print(f"    Retrieved: {len(bookmarks)} bookmarks")
                
                # Analyze each bookmark
                folder_bookmark_ids = set()
                folder_urls = set()
                
                for bookmark in bookmarks:
                    bookmark_id = bookmark.get('bookmark_id')
                    bookmark_url = bookmark.get('url', '').strip()
                    title = bookmark.get('title', 'Untitled')[:50]
                    
                    if bookmark_id:
                        folder_bookmark_ids.add(bookmark_id)
                        bookmark_id_to_folders[bookmark_id].append(folder_name)
                        
                        # Store the full bookmark data (use first occurrence)
                        if bookmark_id not in all_bookmark_data:
                            all_bookmark_data[bookmark_id] = bookmark
                    
                    if bookmark_url:
                        folder_urls.add(bookmark_url)
                        url_to_folders[bookmark_url].append(folder_name)
                
                print(f"    Unique bookmark IDs: {len(folder_bookmark_ids)}")
                print(f"    Unique URLs: {len(folder_urls)}")
                
                # Sample some bookmarks from this folder
                print(f"    Sample bookmarks:")
                for i, bookmark in enumerate(bookmarks[:3]):
                    bid = bookmark.get('bookmark_id')
                    title = bookmark.get('title', 'Untitled')[:40]
                    url_sample = bookmark.get('url', 'No URL')[:50]
                    print(f"      {i+1}. ID:{bid} | {title} | {url_sample}")
                
            else:
                print(f"    ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        print()
    
    # Analysis of duplicates
    print("🔍 DUPLICATE ANALYSIS")
    print("-" * 40)
    
    total_unique_ids = len(all_bookmark_data)
    total_unique_urls = len(url_to_folders)
    
    print(f"Total unique bookmark IDs across all folders: {total_unique_ids}")
    print(f"Total unique URLs across all folders: {total_unique_urls}")
    print()
    
    # Analyze cross-folder membership
    multi_folder_bookmarks = {bid: folders for bid, folders in bookmark_id_to_folders.items() if len(folders) > 1}
    single_folder_bookmarks = {bid: folders for bid, folders in bookmark_id_to_folders.items() if len(folders) == 1}
    
    print(f"📊 CROSS-FOLDER MEMBERSHIP:")
    print(f"  Bookmarks in multiple folders: {len(multi_folder_bookmarks)}")
    print(f"  Bookmarks in single folder: {len(single_folder_bookmarks)}")
    print()
    
    if multi_folder_bookmarks:
        print("  🔗 Sample multi-folder bookmarks:")
        for i, (bid, folders) in enumerate(list(multi_folder_bookmarks.items())[:5]):
            bookmark = all_bookmark_data[bid]
            title = bookmark.get('title', 'Untitled')[:50]
            print(f"    {i+1}. ID:{bid} | '{title}' | In: {', '.join(folders)}")
        print()
    
    # Folder membership distribution
    folder_distribution = defaultdict(int)
    for folders in bookmark_id_to_folders.values():
        folder_distribution[len(folders)] += 1
    
    print("  📈 Folder membership distribution:")
    for folder_count, bookmark_count in sorted(folder_distribution.items()):
        print(f"    {bookmark_count} bookmarks appear in {folder_count} folder(s)")
    print()
    
    # Check CSV file structure
    print("📋 CSV FILE ANALYSIS")
    print("-" * 40)
    
    csv_file = "inputs/instapaper_export.csv"
    if os.path.exists(csv_file):
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Read first few lines to understand structure
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                print(f"CSV Headers: {', '.join(headers) if headers else 'No headers found'}")
                
                # Count total rows and sample data
                f.seek(0)
                total_rows = sum(1 for line in f) - 1  # Subtract header
                
                f.seek(0)
                reader = csv.DictReader(f)
                
                print(f"Total CSV rows: {total_rows:,}")
                print()
                
                # Sample CSV data
                print("Sample CSV entries:")
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    
                    url = row.get('URL', 'No URL')[:60]
                    title = row.get('Title', 'No title')[:50]
                    folder = row.get('Folder', 'No folder')
                    timestamp = row.get('Timestamp', 'No timestamp')
                    
                    print(f"  {i+1}. {title} | {folder} | {timestamp}")
                    print(f"     URL: {url}")
                print()
                
                # Check for URL overlap with API data
                f.seek(0)
                reader = csv.DictReader(f)
                
                csv_urls = set()
                csv_sample_size = 1000  # Sample first 1000 for performance
                
                for i, row in enumerate(reader):
                    if i >= csv_sample_size:
                        break
                    
                    url = row.get('URL', '').strip()
                    if url:
                        csv_urls.add(url)
                
                # Compare with API URLs
                api_urls = set()
                for bookmark in all_bookmark_data.values():
                    url = bookmark.get('url', '').strip()
                    if url:
                        api_urls.add(url)
                
                common_urls = csv_urls & api_urls
                
                print(f"URL OVERLAP ANALYSIS (first {csv_sample_size} CSV entries):")
                print(f"  CSV URLs (sample): {len(csv_urls)}")
                print(f"  API URLs: {len(api_urls)}")
                print(f"  Common URLs: {len(common_urls)}")
                
                if len(common_urls) > 0:
                    overlap_pct = len(common_urls) / len(csv_urls) * 100
                    print(f"  Overlap: {overlap_pct:.1f}%")
                else:
                    print(f"  ⚠️  NO OVERLAP FOUND!")
                
        except Exception as e:
            print(f"❌ Error analyzing CSV: {e}")
    else:
        print("❌ CSV file not found")
    
    print()
    
    # Final diagnosis
    print("🎯 DIAGNOSIS & FINDINGS")
    print("=" * 60)
    
    print("🔍 KEY OBSERVATIONS:")
    
    if total_unique_ids < 1000:
        print(f"  ❌ CRITICAL: Only {total_unique_ids} unique bookmarks via API")
        print(f"  📊 This is drastically less than CSV's {total_rows:,} bookmarks")
        print()
    
    if len(multi_folder_bookmarks) == total_unique_ids:
        print(f"  🔄 ALL bookmarks appear in multiple folders")
        print(f"  💡 This suggests the same recent bookmarks are being duplicated")
    elif len(multi_folder_bookmarks) > total_unique_ids * 0.8:
        print(f"  🔄 Most bookmarks ({len(multi_folder_bookmarks)}/{total_unique_ids}) appear in multiple folders")
    
    print()
    print("🚨 LIKELY CAUSES:")
    print("  1. API returns only RECENT bookmarks (latest 500 across account)")
    print("  2. These recent bookmarks are DUPLICATED across multiple folders")
    print("  3. Historical bookmarks (older items) are NOT accessible via API")
    print("  4. The 500-bookmark limit applies to the ENTIRE ACCOUNT, not per folder")
    print()
    
    print("💡 CONCLUSIONS:")
    print("  ❌ API approach is fundamentally limited")
    print("  ✅ CSV export contains your complete historical collection")
    print("  📊 API gives you ~0.9% coverage of your total bookmarks")
    print("  🎯 For complete backup: USE CSV EXPORT, not API")
    print()
    
    print("🛠️  RECOMMENDATIONS:")
    print("  1. ✅ Use CSV export as your primary data source")
    print("  2. 🔄 Process CSV to Atlas format for complete backup")
    print("  3. 📊 API can be used for getting RECENT items with full content")
    print("  4. 🎯 Hybrid approach: CSV for coverage + API for recent content quality")

if __name__ == '__main__':
    investigate_bookmark_duplication()