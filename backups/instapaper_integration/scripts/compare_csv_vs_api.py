#!/usr/bin/env python3
"""
Compare CSV export data vs API extracted data to find what's missing
"""

import json
import csv
import os
from urllib.parse import urlparse
from datetime import datetime

def compare_csv_vs_api():
    """Compare the massive CSV export against our API extraction"""
    
    print("🔍 COMPARING CSV EXPORT vs API EXTRACTION")
    print("=" * 60)
    
    # Load API extraction data
    api_file = "backups/instapaper_complete_extraction_2025-08-05-complete.json"
    csv_file = "inputs/instapaper_export.csv"
    
    if not os.path.exists(api_file):
        print(f"❌ API backup file not found: {api_file}")
        return
        
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    print("📚 Loading API extraction data...")
    with open(api_file, 'r', encoding='utf-8') as f:
        api_data = json.load(f)
    
    # Extract all unique URLs from API data
    api_urls = set()
    api_bookmarks = {}
    
    folders = api_data.get('folders', {})
    for folder_name, folder_data in folders.items():
        if isinstance(folder_data, dict) and 'bookmarks' in folder_data:
            for bookmark in folder_data['bookmarks']:
                url = bookmark.get('url', '').strip()
                if url:
                    api_urls.add(url)
                    api_bookmarks[url] = bookmark
    
    print(f"  ✅ API data loaded: {len(api_urls)} unique URLs")
    
    # Load CSV data
    print("📄 Loading CSV export data...")
    csv_urls = set()
    csv_bookmarks = {}
    csv_row_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                csv_row_count += 1
                url = row.get('URL', '').strip()
                
                if url and url != 'URL':  # Skip header if it appears as data
                    csv_urls.add(url)
                    csv_bookmarks[url] = {
                        'url': url,
                        'title': row.get('Title', ''),
                        'folder': row.get('Folder', ''),
                        'timestamp': row.get('Timestamp', ''),
                        'selection': row.get('Selection', ''),
                        'tags': row.get('Tags', ''),
                        'csv_row': csv_row_count
                    }
                
                # Progress indicator for large file
                if csv_row_count % 5000 == 0:
                    print(f"    Processing CSV row: {csv_row_count}")
        
        print(f"  ✅ CSV data loaded: {csv_row_count} total rows, {len(csv_urls)} unique URLs")
        
    except Exception as e:
        print(f"  ❌ Error loading CSV: {e}")
        return
    
    print()
    
    # Analysis
    print("🔍 COMPARISON ANALYSIS")
    print("-" * 50)
    
    # URLs in both
    common_urls = api_urls & csv_urls
    print(f"📊 URLs in both API and CSV: {len(common_urls)}")
    
    # URLs only in API
    api_only = api_urls - csv_urls
    print(f"🔗 URLs only in API extraction: {len(api_only)}")
    
    # URLs only in CSV (this is the big one!)
    csv_only = csv_urls - api_urls
    print(f"📋 URLs only in CSV export: {len(csv_only)} ⚠️")
    
    print()
    print(f"🎯 COVERAGE ANALYSIS:")
    print(f"  CSV has {len(csv_urls)} total URLs")
    print(f"  API captured {len(api_urls)} URLs")
    print(f"  Coverage: {len(common_urls)/len(csv_urls)*100:.1f}%")
    print(f"  Missing from API: {len(csv_only)} URLs ({len(csv_only)/len(csv_urls)*100:.1f}%)")
    
    print()
    
    # Analyze what's missing
    print("🔍 ANALYZING MISSING CONTENT")
    print("-" * 50)
    
    # Sample of missing URLs
    print("📋 Sample of URLs missing from API extraction:")
    missing_samples = list(csv_only)[:10]
    
    for i, url in enumerate(missing_samples, 1):
        csv_bookmark = csv_bookmarks[url]
        title = csv_bookmark['title'][:60]
        folder = csv_bookmark['folder']
        
        print(f"  {i:2d}. {title}")
        print(f"      URL: {url}")
        print(f"      Folder: {folder}")
        print()
    
    # Analyze missing content by folder
    print("📁 Missing content by folder:")
    missing_by_folder = {}
    
    for url in csv_only:
        csv_bookmark = csv_bookmarks[url]
        folder = csv_bookmark['folder']
        missing_by_folder[folder] = missing_by_folder.get(folder, 0) + 1
    
    for folder, count in sorted(missing_by_folder.items(), key=lambda x: x[1], reverse=True):
        print(f"  {folder:20} | {count:5,} missing URLs")
    
    print()
    
    # Analyze URL patterns
    print("🔍 ANALYZING URL PATTERNS")
    print("-" * 50)
    
    # Check for private content in CSV
    csv_private = [url for url in csv_urls if url.startswith('instapaper://private-content/')]
    api_private = [url for url in api_urls if url.startswith('instapaper://private-content/')]
    
    print(f"📧 Private content URLs:")
    print(f"  CSV has: {len(csv_private)} private URLs")
    print(f"  API has: {len(api_private)} private URLs")
    print(f"  Missing private: {len(csv_private) - len(api_private)}")
    
    # Check for regular HTTP URLs
    csv_http = [url for url in csv_urls if url.startswith(('http://', 'https://'))]
    api_http = [url for url in api_urls if url.startswith(('http://', 'https://'))]
    
    print(f"🌐 Regular HTTP URLs:")
    print(f"  CSV has: {len(csv_http)} HTTP URLs")  
    print(f"  API has: {len(api_http)} HTTP URLs")
    print(f"  Missing HTTP: {len(csv_http) - len(api_http)}")
    
    print()
    
    # Time analysis
    print("📅 TIME PERIOD ANALYSIS")
    print("-" * 50)
    
    # Convert timestamps and analyze date ranges
    csv_timestamps = []
    for url in common_urls:
        csv_bookmark = csv_bookmarks[url]
        timestamp_str = csv_bookmark['timestamp']
        if timestamp_str.isdigit():
            try:
                timestamp = int(timestamp_str)
                dt = datetime.fromtimestamp(timestamp)
                csv_timestamps.append(dt)
            except:
                pass
    
    if csv_timestamps:
        csv_timestamps.sort()
        oldest = csv_timestamps[0]
        newest = csv_timestamps[-1]
        
        print(f"📊 Date range of captured bookmarks:")
        print(f"  Oldest: {oldest.strftime('%Y-%m-%d')}")
        print(f"  Newest: {newest.strftime('%Y-%m-%d')}")
        print(f"  Span: {(newest - oldest).days} days")
        
        # Check if missing content is older
        missing_timestamps = []
        for url in list(csv_only)[:1000]:  # Sample for performance
            csv_bookmark = csv_bookmarks[url]
            timestamp_str = csv_bookmark['timestamp']
            if timestamp_str.isdigit():
                try:
                    timestamp = int(timestamp_str)
                    dt = datetime.fromtimestamp(timestamp)
                    missing_timestamps.append(dt)
                except:
                    pass
        
        if missing_timestamps:
            missing_timestamps.sort()
            missing_oldest = missing_timestamps[0]
            missing_newest = missing_timestamps[-1]
            
            print(f"📊 Date range of MISSING bookmarks (sample):")
            print(f"  Oldest: {missing_oldest.strftime('%Y-%m-%d')}")
            print(f"  Newest: {missing_newest.strftime('%Y-%m-%d')}")
    
    print()
    
    # Summary and recommendations
    print("🎯 SUMMARY & RECOMMENDATIONS")
    print("=" * 60)
    print(f"🔢 You have {len(csv_urls):,} total bookmarks in your CSV export")
    print(f"📊 API only captured {len(api_urls):,} bookmarks ({len(api_urls)/len(csv_urls)*100:.1f}%)")
    print(f"❌ Missing {len(csv_only):,} bookmarks from API extraction")
    print()
    
    if len(csv_only) > len(api_urls):
        print("⚠️  MAJOR GAP: API is missing the majority of your bookmarks!")
        print("💡 Likely causes:")
        print("   1. API free tier limits historical data")
        print("   2. Old bookmarks not accessible via API")
        print("   3. Folder limitations (API might not see archived content)")
        print("   4. Account-level API restrictions")
        print()
        print("🔧 Recommendations:")
        print("   1. The CSV export contains your complete collection")
        print("   2. Use CSV as primary data source")
        print("   3. API data for recent/clean content only")
        print("   4. Hybrid approach: CSV for coverage, API for content quality")

if __name__ == '__main__':
    compare_csv_vs_api()