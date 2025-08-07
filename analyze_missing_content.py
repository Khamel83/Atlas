#\!/usr/bin/env python3
"""
Analyze what content is still missing from Atlas collection
"""

import os
import csv
import json
from collections import defaultdict, Counter
from urllib.parse import urlparse

def analyze_missing_content():
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
    
    return {
        'total_missing': len(missing_urls),
        'missing_with_content': len(missing_with_content),
        'missing_urls': missing_urls,
        'missing_domains': dict(missing_domains.most_common(10))
    }

if __name__ == '__main__':
    analyze_missing_content()
EOF < /dev/null