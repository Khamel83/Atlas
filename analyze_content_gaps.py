#!/usr/bin/env python3
"""
Analyze content quality gaps - items that were converted but have minimal content
"""

import os
import csv
import json
import glob
import hashlib
from collections import defaultdict, Counter
from urllib.parse import urlparse
from datetime import datetime

def analyze_content_gaps():
    """Analyze items that were converted but have minimal/no actual content"""
    
    print("🔍 ANALYZING CONTENT QUALITY GAPS")
    print("=" * 60)
    
    # Load Instapaper source data
    csv_file = "inputs/instapaper_export.csv"
    instapaper_items = load_instapaper_with_expectations(csv_file)
    
    # Analyze Atlas collection for content quality
    content_analysis = analyze_atlas_content_quality()
    
    # Identify content gaps
    identify_content_gaps(instapaper_items, content_analysis)

def load_instapaper_with_expectations(csv_file):
    """Load Instapaper items with expected content analysis"""
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return {}
    
    items = {}
    categories = {
        'private_newsletters': 0,
        'web_with_selection': 0,
        'web_without_selection': 0,
        'domains': defaultdict(int)
    }
    
    print("📚 Analyzing Instapaper source expectations...")
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                url = row.get('URL', '').strip()
                title = row.get('Title', 'Untitled').strip()
                timestamp = row.get('Timestamp', '').strip()
                selection = row.get('Selection', '').strip()
                folder = row.get('Folder', 'Unknown').strip()
                
                # Generate UID
                uid = generate_instapaper_uid(url, title, timestamp)
                
                # Categorize expected content
                is_private = url.startswith('instapaper-private://')
                is_web_url = url.startswith('http')
                has_selection = len(selection.strip()) > 50
                domain = extract_domain(url) if is_web_url else 'private' if is_private else 'other'
                
                if is_private:
                    categories['private_newsletters'] += 1
                elif is_web_url:
                    categories['domains'][domain] += 1
                    if has_selection:
                        categories['web_with_selection'] += 1
                    else:
                        categories['web_without_selection'] += 1
                
                items[uid] = {
                    'uid': uid,
                    'url': url,
                    'title': title,
                    'timestamp': timestamp,
                    'selection': selection,
                    'folder': folder,
                    'selection_length': len(selection) if selection else 0,
                    'is_private': is_private,
                    'is_web_url': is_web_url,
                    'has_substantial_selection': has_selection,
                    'domain': domain,
                    'expected_content_type': 'full' if (is_private or has_selection) else 'minimal'
                }
    
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return {}
    
    print(f"  ✅ Analyzed {len(items):,} Instapaper items")
    print(f"  📧 Private newsletters: {categories['private_newsletters']:,} (expected full content via API)")
    print(f"  📝 Web articles with selection: {categories['web_with_selection']:,} (expected selection content)")
    print(f"  📄 Web articles without selection: {categories['web_without_selection']:,} (expected minimal content)")
    
    # Show top domains
    print(f"  🌐 Top domains:")
    top_domains = sorted(categories['domains'].items(), key=lambda x: x[1], reverse=True)[:10]
    for domain, count in top_domains:
        print(f"    {domain}: {count:,} articles")
    
    return items

def analyze_atlas_content_quality():
    """Analyze actual content quality in Atlas collection"""
    
    print(f"\n📁 Analyzing Atlas content quality...")
    
    quality_stats = {
        'total_files': 0,
        'by_content_quality': {
            'full_content': 0,      # >1000 chars of real content
            'moderate_content': 0,   # 200-1000 chars
            'minimal_content': 0,    # 50-200 chars  
            'stub_content': 0        # <50 chars
        },
        'by_source_type': defaultdict(int),
        'private_newsletters': 0,
        'web_articles': 0
    }
    
    # Analyze markdown files for content
    md_dir = "output/articles/markdown"
    metadata_dir = "output/articles/metadata"
    
    if not os.path.exists(md_dir):
        print(f"  ❌ Markdown directory not found")
        return quality_stats
    
    md_files = [f for f in os.listdir(md_dir) if f.endswith('.md')]
    quality_stats['total_files'] = len(md_files)
    
    print(f"  📊 Analyzing {len(md_files):,} Atlas articles...")
    
    for md_file in md_files:
        try:
            # Read markdown content
            with open(os.path.join(md_dir, md_file), 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract actual article content (skip metadata)
            content_lines = content.split('\n')
            article_content = []
            in_metadata = True
            
            for line in content_lines:
                if in_metadata and line.strip() == '---' and article_content == []:
                    continue
                elif in_metadata and line.strip() == '---':
                    in_metadata = False
                    continue
                elif not in_metadata:
                    article_content.append(line)
            
            # Analyze content quality
            full_content = '\n'.join(article_content).strip()
            content_length = len(full_content)
            
            # Categorize by content quality
            if content_length > 1000:
                quality_stats['by_content_quality']['full_content'] += 1
            elif content_length > 200:
                quality_stats['by_content_quality']['moderate_content'] += 1
            elif content_length > 50:
                quality_stats['by_content_quality']['minimal_content'] += 1
            else:
                quality_stats['by_content_quality']['stub_content'] += 1
            
            # Check metadata for source type
            uid = md_file.replace('.md', '')
            metadata_file = os.path.join(metadata_dir, f"{uid}.json")
            
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    source = metadata.get('source', '')
                    fetch_method = metadata.get('fetch_method', '')
                    
                    if 'instapaper_api_private_content' in fetch_method:
                        quality_stats['private_newsletters'] += 1
                    elif source.startswith('http'):
                        quality_stats['web_articles'] += 1
                        domain = extract_domain(source)
                        quality_stats['by_source_type'][domain] += 1
                        
                except:
                    pass
                    
        except Exception as e:
            # Skip problematic files
            continue
    
    print(f"  ✅ Content quality analysis complete")
    print(f"  📊 Full content (>1K chars): {quality_stats['by_content_quality']['full_content']:,}")
    print(f"  📄 Moderate content (200-1K chars): {quality_stats['by_content_quality']['moderate_content']:,}")  
    print(f"  📝 Minimal content (50-200 chars): {quality_stats['by_content_quality']['minimal_content']:,}")
    print(f"  🔥 Stub content (<50 chars): {quality_stats['by_content_quality']['stub_content']:,}")
    print(f"  📧 Private newsletters: {quality_stats['private_newsletters']:,}")
    print(f"  🌐 Web articles: {quality_stats['web_articles']:,}")
    
    return quality_stats

def identify_content_gaps(instapaper_items, content_analysis):
    """Identify specific content gaps and opportunities"""
    
    print(f"\n🎯 CONTENT GAP ANALYSIS")
    print("-" * 40)
    
    # Calculate content success rates
    total_files = content_analysis['total_files']
    full_content = content_analysis['by_content_quality']['full_content']
    moderate_content = content_analysis['by_content_quality']['moderate_content']
    stub_content = content_analysis['by_content_quality']['stub_content']
    
    substantial_content = full_content + moderate_content
    
    print(f"📊 CONTENT QUALITY RESULTS:")
    print(f"  Total Atlas articles: {total_files:,}")
    print(f"  Substantial content: {substantial_content:,} ({substantial_content/total_files*100:.1f}%)")
    print(f"  Stub/minimal content: {stub_content:,} ({stub_content/total_files*100:.1f}%)")
    
    # Analyze gaps by source expectations
    print(f"\n🔍 EXPECTED vs ACTUAL CONTENT:")
    
    # Private newsletters
    expected_private = sum(1 for item in instapaper_items.values() if item['is_private'])
    actual_private = content_analysis['private_newsletters']
    
    print(f"  📧 Private newsletters:")
    print(f"    Expected in CSV: {expected_private:,}")
    print(f"    With full content in Atlas: {actual_private:,}")
    print(f"    Gap: {expected_private - actual_private:,} (historical items beyond API access)")
    
    # Web articles with selection
    expected_selection = sum(1 for item in instapaper_items.values() if item['has_substantial_selection'])
    
    print(f"  📝 Web articles with selection content:")
    print(f"    Expected selection content available: {expected_selection:,}")
    print(f"    Potential extraction opportunity if selection content not fully utilized")
    
    # Domain analysis for missing full content
    print(f"\n🌐 DOMAIN CONTENT ANALYSIS:")
    
    # Count expected vs stub content by domain
    expected_by_domain = defaultdict(int)
    for item in instapaper_items.values():
        if item['is_web_url']:
            expected_by_domain[item['domain']] += 1
    
    print(f"  Top domains that might have extractable content:")
    top_expected = sorted(expected_by_domain.items(), key=lambda x: x[1], reverse=True)[:10]
    
    for domain, expected_count in top_expected:
        print(f"    {domain}: {expected_count:,} articles")
        
        # Sample some titles from this domain
        domain_items = [item for item in instapaper_items.values() 
                       if item['domain'] == domain and item['has_substantial_selection']][:3]
        
        if domain_items:
            print(f"      Sample items with selection content:")
            for item in domain_items:
                title_preview = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
                selection_preview = item['selection'][:100] + "..." if len(item['selection']) > 100 else item['selection']
                print(f"        • {title_preview}")
                print(f"          Selection: {selection_preview}")

def generate_instapaper_uid(url, title, timestamp):
    """Generate the same UID as our conversion scripts"""
    unique_string = f"{url}|{title}|{timestamp}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()[:16]

def extract_domain(url):
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return 'unknown'

if __name__ == '__main__':
    analyze_content_gaps()