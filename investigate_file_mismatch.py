#!/usr/bin/env python3
"""
Investigate file count mismatch and create comprehensive URL extraction plan
"""

import os
import json
import csv
import glob
from collections import defaultdict
from urllib.parse import urlparse

def investigate_file_mismatch():
    """Find out why we have different counts of HTML/MD vs metadata files"""
    
    print("🔍 INVESTIGATING FILE COUNT MISMATCH")
    print("=" * 60)
    
    # Get all files
    html_files = set([f.replace('.html', '') for f in os.listdir('output/articles/html') if f.endswith('.html')])
    md_files = set([f.replace('.md', '') for f in os.listdir('output/articles/markdown') if f.endswith('.md')])  
    metadata_files = set([f.replace('.json', '') for f in os.listdir('output/articles/metadata') if f.endswith('.json')])
    
    print(f"📊 File counts:")
    print(f"  HTML files: {len(html_files):,}")
    print(f"  Markdown files: {len(md_files):,}")
    print(f"  Metadata files: {len(metadata_files):,}")
    
    # Find mismatches
    only_metadata = metadata_files - html_files
    only_html = html_files - metadata_files
    only_md = md_files - html_files
    
    print(f"\n🔍 Mismatch analysis:")
    print(f"  Only metadata (no HTML/MD): {len(only_metadata)}")
    print(f"  Only HTML (no metadata): {len(only_html)}")
    print(f"  HTML/MD mismatch: {len(only_md)}")
    
    # Investigate metadata-only files
    if only_metadata:
        print(f"\n📋 Sample metadata-only files:")
        for i, uid in enumerate(list(only_metadata)[:5]):
            try:
                with open(f'output/articles/metadata/{uid}.json', 'r') as f:
                    metadata = json.load(f)
                print(f"  {i+1}. {uid}: {metadata.get('title', 'No title')}")
                print(f"     Source: {metadata.get('source', 'No source')}")
                print(f"     Content type: {metadata.get('content_type', 'Unknown')}")
            except:
                print(f"  {i+1}. {uid}: Error reading metadata")
    
    return {
        'html_count': len(html_files),
        'md_count': len(md_files), 
        'metadata_count': len(metadata_files),
        'only_metadata': only_metadata,
        'only_html': only_html
    }

def create_comprehensive_url_list():
    """Create deduplicated list of ALL URLs from both API and CSV"""
    
    print(f"\n📝 CREATING COMPREHENSIVE DEDUPLICATED URL LIST")
    print("=" * 60)
    
    all_urls = set()
    url_sources = defaultdict(list)  # Track where each URL came from
    url_details = {}  # Store details for each URL
    
    # 1. Extract URLs from current Atlas metadata
    print("📁 Extracting URLs from Atlas collection...")
    atlas_urls = 0
    
    if os.path.exists('output/articles/metadata'):
        for metadata_file in os.listdir('output/articles/metadata'):
            if metadata_file.endswith('.json'):
                try:
                    with open(f'output/articles/metadata/{metadata_file}', 'r') as f:
                        metadata = json.load(f)
                    
                    source = metadata.get('source', '').strip()
                    if source and source not in ['', 'unknown', 'about:blank']:
                        all_urls.add(source)
                        url_sources[source].append('atlas')
                        atlas_urls += 1
                        
                        if source not in url_details:
                            url_details[source] = {
                                'title': metadata.get('title', ''),
                                'content_type': metadata.get('content_type', ''),
                                'fetch_method': metadata.get('fetch_method', ''),
                                'folder': metadata.get('type_specific', {}).get('folder', ''),
                                'has_content': 'selection' in metadata.get('content_type', '') or 'private' in metadata.get('fetch_method', '')
                            }
                except:
                    continue
    
    print(f"  ✅ Atlas URLs: {atlas_urls:,}")
    
    # 2. Extract URLs from original CSV
    print("📚 Extracting URLs from original CSV...")
    csv_urls = 0
    
    csv_file = "inputs/instapaper_export.csv"
    if os.path.exists(csv_file):
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    url = row.get('URL', '').strip()
                    if url and url not in ['', 'unknown', 'about:blank']:
                        all_urls.add(url)
                        url_sources[url].append('csv')
                        csv_urls += 1
                        
                        if url not in url_details:
                            url_details[url] = {
                                'title': row.get('Title', ''),
                                'content_type': 'from_csv',
                                'fetch_method': 'csv_export',
                                'folder': row.get('Folder', ''),
                                'has_content': len(row.get('Selection', '').strip()) > 100,
                                'selection_length': len(row.get('Selection', '').strip())
                            }
        except Exception as e:
            print(f"  ❌ Error reading CSV: {e}")
    
    print(f"  ✅ CSV URLs: {csv_urls:,}")
    
    # 3. Extract URLs from API batch files
    print("📡 Extracting URLs from API extractions...")
    api_urls = 0
    
    batch_files = glob.glob('private_newsletter_batch_*.json')
    for batch_file in batch_files:
        try:
            with open(batch_file, 'r') as f:
                batch_data = json.load(f)
            
            extracted_content = batch_data.get('extracted_content', {})
            for content_data in extracted_content.values():
                url = content_data.get('url', '').strip()
                if url and url not in ['', 'unknown', 'about:blank']:
                    all_urls.add(url)
                    url_sources[url].append('api_private')
                    api_urls += 1
                    
                    if url not in url_details:
                        url_details[url] = {
                            'title': content_data.get('title', ''),
                            'content_type': 'private_newsletter_api',
                            'fetch_method': 'instapaper_api_private_content',
                            'folder': 'private_extraction',
                            'has_content': True,
                            'content_length': content_data.get('content_length', 0)
                        }
        except:
            continue
    
    print(f"  ✅ API URLs: {api_urls:,}")
    
    # 4. Deduplicate and categorize
    print(f"\n📊 DEDUPLICATION RESULTS:")
    print(f"  Total unique URLs: {len(all_urls):,}")
    
    # Categorize URLs
    url_categories = {
        'web_urls': [],
        'private_newsletters': [],
        'other_urls': []
    }
    
    domain_counts = defaultdict(int)
    
    for url in all_urls:
        if url.startswith('http'):
            url_categories['web_urls'].append(url)
            try:
                domain = urlparse(url).netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                domain_counts[domain] += 1
            except:
                domain_counts['unknown'] += 1
                
        elif url.startswith('instapaper-private://'):
            url_categories['private_newsletters'].append(url)
        else:
            url_categories['other_urls'].append(url)
    
    print(f"  🌐 Web URLs: {len(url_categories['web_urls']):,}")
    print(f"  📧 Private newsletters: {len(url_categories['private_newsletters']):,}")
    print(f"  🔗 Other URLs: {len(url_categories['other_urls']):,}")
    
    print(f"\n🌐 Top domains:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {domain}: {count:,} URLs")
    
    # 5. Create comprehensive CSV
    print(f"\n📄 Creating comprehensive URL CSV...")
    
    csv_rows = []
    for url in sorted(all_urls):
        details = url_details.get(url, {})
        sources = ','.join(url_sources[url])
        
        csv_rows.append({
            'url': url,
            'title': details.get('title', ''),
            'sources': sources,
            'content_type': details.get('content_type', ''),
            'fetch_method': details.get('fetch_method', ''),
            'folder': details.get('folder', ''),
            'has_content': details.get('has_content', False),
            'content_indicator': details.get('selection_length', details.get('content_length', 0)),
            'url_type': 'web' if url.startswith('http') else 'private' if url.startswith('instapaper-private://') else 'other'
        })
    
    csv_filename = f"comprehensive_instapaper_urls_{len(all_urls)}_deduplicated.csv"
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'title', 'sources', 'content_type', 'fetch_method', 'folder', 'has_content', 'content_indicator', 'url_type'])
        writer.writeheader()
        writer.writerows(csv_rows)
    
    print(f"  ✅ Saved: {csv_filename}")
    print(f"  📊 Total URLs: {len(csv_rows):,}")
    
    return {
        'total_urls': len(all_urls),
        'web_urls': len(url_categories['web_urls']),
        'private_urls': len(url_categories['private_newsletters']),
        'csv_filename': csv_filename,
        'domain_counts': dict(domain_counts)
    }

def analyze_private_newsletter_gap():
    """Analyze the private newsletter extraction gap"""
    
    print(f"\n📧 PRIVATE NEWSLETTER GAP ANALYSIS")
    print("=" * 60)
    
    # Count private newsletters in CSV
    csv_private = 0
    csv_file = "inputs/instapaper_export.csv"
    
    if os.path.exists(csv_file):
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('URL', '').strip()
                if url.startswith('instapaper-private://'):
                    csv_private += 1
    
    # Count what we extracted
    extracted_private = 137  # From our analysis
    
    # The gap
    gap = csv_private - extracted_private
    
    print(f"📊 Private Newsletter Numbers:")
    print(f"  In original CSV: {csv_private:,}")
    print(f"  Successfully extracted: {extracted_private:,}")
    print(f"  Gap: {gap:,} ({gap/csv_private*100:.1f}% missing)")
    
    print(f"\n🔍 Why the gap exists:")
    print(f"  ❌ API limitation: Only ~150 recent private newsletters have extractable content")
    print(f"  📧 Historical newsletters: {gap:,} exist as metadata only in CSV")
    print(f"  🚫 Content access: Historical private content not accessible via API")
    
    print(f"\n🎯 Next steps for private newsletters:")
    print(f"  1. 🧪 Test folder redistribution strategy (might unlock 20-100 more)")
    print(f"  2. 🔍 Look for alternative private newsletter access methods")
    print(f"  3. 📧 Consider email-based extraction if newsletters came via email")
    
    return {
        'csv_private': csv_private,
        'extracted_private': extracted_private,
        'gap': gap,
        'gap_percentage': gap/csv_private*100 if csv_private > 0 else 0
    }

if __name__ == '__main__':
    print("🚀 COMPREHENSIVE INSTAPAPER INVESTIGATION")
    print("=" * 70)
    
    mismatch_results = investigate_file_mismatch()
    url_results = create_comprehensive_url_list()
    private_gap = analyze_private_newsletter_gap()
    
    print(f"\n🎯 SUMMARY:")
    print(f"  File mismatch identified: {mismatch_results['metadata_count'] - mismatch_results['html_count']} metadata files without HTML/MD")
    print(f"  Total unique URLs found: {url_results['total_urls']:,}")
    print(f"  Private newsletter gap: {private_gap['gap']:,} newsletters ({private_gap['gap_percentage']:.1f}%)")
    print(f"  Comprehensive URL CSV: {url_results['csv_filename']}")