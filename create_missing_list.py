#!/usr/bin/env python3
"""
Create list of missing content from Instapaper
"""

import os
import csv
import json
from collections import defaultdict, Counter
from urllib.parse import urlparse

def create_missing_list():
    """Create comprehensive lists of missing content"""
    
    print("🔍 ANALYZING MISSING CONTENT FROM INSTAPAPER")
    print("=" * 60)
    
    # Load comprehensive URL list
    comprehensive_csv = "comprehensive_instapaper_urls_6712_deduplicated.csv"
    
    if not os.path.exists(comprehensive_csv):
        print(f"❌ Cannot find {comprehensive_csv}")
        return
    
    print(f"📚 Loading comprehensive URL list from {comprehensive_csv}...")
    
    all_urls = []
    with open(comprehensive_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_urls.append(row)
    
    print(f"  ✅ Loaded {len(all_urls):,} total URLs from Instapaper")
    
    # Get what's currently in Atlas
    print(f"\n📁 Scanning current Atlas collection...")
    
    atlas_urls = set()
    if os.path.exists('output/articles/metadata'):
        for metadata_file in os.listdir('output/articles/metadata'):
            if metadata_file.endswith('.json'):
                try:
                    with open(f'output/articles/metadata/{metadata_file}', 'r') as f:
                        metadata = json.load(f)
                    
                    source = metadata.get('source', '').strip()
                    if source and source not in ['', 'unknown', 'about:blank']:
                        atlas_urls.add(source)
                except:
                    continue
    
    print(f"  ✅ Found {len(atlas_urls):,} URLs already in Atlas")
    
    # Analyze what's missing
    print(f"\n🔍 Analyzing missing content...")
    
    missing_urls = []
    missing_by_type = defaultdict(list)
    missing_by_folder = defaultdict(list)
    missing_with_content = []
    missing_domains = Counter()
    
    for url_data in all_urls:
        url = url_data['url'].strip()
        
        if url not in atlas_urls:
            missing_urls.append(url_data)
            
            url_type = url_data.get('url_type', 'unknown')
            folder = url_data.get('folder', 'unknown')
            has_content = url_data.get('has_content', 'False').lower() == 'true'
            
            missing_by_type[url_type].append(url_data)
            missing_by_folder[folder].append(url_data)
            
            if has_content:
                missing_with_content.append(url_data)
            
            # Domain analysis
            if url.startswith('http'):
                try:
                    domain = urlparse(url).netloc.lower()
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    missing_domains[domain] += 1
                except:
                    missing_domains['unknown'] += 1
    
    print(f"📊 MISSING CONTENT SUMMARY")
    print("-" * 40)
    print(f"  Total URLs in Instapaper: {len(all_urls):,}")
    print(f"  URLs in Atlas: {len(atlas_urls):,}")
    print(f"  Missing URLs: {len(missing_urls):,} ({len(missing_urls)/len(all_urls)*100:.1f}%)")
    print(f"  Missing with content: {len(missing_with_content):,}")
    
    # Missing by type
    print(f"\n📋 MISSING BY TYPE:")
    for url_type, items in sorted(missing_by_type.items(), key=lambda x: len(x[1]), reverse=True):
        with_content = sum(1 for item in items if item.get('has_content', 'False').lower() == 'true')
        print(f"  {url_type}: {len(items):,} URLs ({with_content:,} with content)")
    
    # Missing by folder
    print(f"\n📂 MISSING BY FOLDER:")
    for folder, items in sorted(missing_by_folder.items(), key=lambda x: len(x[1]), reverse=True):
        with_content = sum(1 for item in items if item.get('has_content', 'False').lower() == 'true')
        print(f"  {folder}: {len(items):,} URLs ({with_content:,} with content)")
    
    # Top missing domains
    print(f"\n🌐 TOP 15 MISSING DOMAINS:")
    for domain, count in missing_domains.most_common(15):
        print(f"  {domain}: {count:,} URLs")
    
    # Create missing content files
    print(f"\n📄 Creating missing content files...")
    
    # 1. All missing URLs
    missing_all_file = "MISSING_CONTENT_ALL.csv"
    with open(missing_all_file, 'w', newline='', encoding='utf-8') as f:
        if missing_urls:
            fieldnames = missing_urls[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(missing_urls)
    
    print(f"  ✅ All missing: {missing_all_file} ({len(missing_urls):,} URLs)")
    
    # 2. Missing with content (priority)
    missing_priority_file = "MISSING_CONTENT_PRIORITY.csv"
    with open(missing_priority_file, 'w', newline='', encoding='utf-8') as f:
        if missing_with_content:
            fieldnames = missing_with_content[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(missing_with_content)
    
    print(f"  ✅ Priority (with content): {missing_priority_file} ({len(missing_with_content):,} URLs)")
    
    # 3. Web URLs only (fetchable)
    missing_web = [item for item in missing_urls if item['url_type'] == 'web']
    missing_web_file = "MISSING_CONTENT_WEB.csv"
    with open(missing_web_file, 'w', newline='', encoding='utf-8') as f:
        if missing_web:
            fieldnames = missing_web[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(missing_web)
    
    print(f"  ✅ Web URLs (fetchable): {missing_web_file} ({len(missing_web):,} URLs)")
    
    # 4. Private newsletters still missing
    missing_private = [item for item in missing_urls if item['url_type'] == 'private']
    missing_private_file = "MISSING_PRIVATE_NEWSLETTERS.csv"
    with open(missing_private_file, 'w', newline='', encoding='utf-8') as f:
        if missing_private:
            fieldnames = missing_private[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(missing_private)
    
    print(f"  ✅ Private newsletters: {missing_private_file} ({len(missing_private):,} URLs)")
    
    print(f"\n🎯 WHAT'S STILL MISSING:")
    print(f"  📧 Private newsletters: {len(missing_private):,} (256 expected from API limit)")
    print(f"  🌐 Web articles: {len(missing_web):,}")
    print(f"  ⭐ URLs with Selection content: {len(missing_with_content):,}")
    
    return {
        'total_missing': len(missing_urls),
        'missing_with_content': len(missing_with_content),
        'missing_web': len(missing_web),
        'missing_private': len(missing_private)
    }

if __name__ == '__main__':
    create_missing_list()