#!/usr/bin/env python3
"""
Comprehensive analysis of current extraction status and remaining opportunities
"""

import os
import json
import csv
import glob
from collections import defaultdict

def analyze_extraction_status():
    """Analyze what we've extracted and what opportunities remain"""
    
    print("🔍 COMPREHENSIVE EXTRACTION ANALYSIS")
    print("=" * 60)
    
    # 1. Analyze CSV source data
    print("📊 STEP 1: CSV SOURCE ANALYSIS")
    print("-" * 40)
    
    csv_file = "inputs/instapaper_export.csv"
    csv_stats = analyze_csv_source(csv_file)
    
    # 2. Analyze API extraction attempts
    print("\n📡 STEP 2: API EXTRACTION ANALYSIS")
    print("-" * 40)
    
    api_stats = analyze_api_extractions()
    
    # 3. Analyze current Atlas collection
    print("\n📁 STEP 3: CURRENT ATLAS COLLECTION")
    print("-" * 40)
    
    atlas_stats = analyze_atlas_collection()
    
    # 4. Identify extraction gaps
    print("\n🎯 STEP 4: EXTRACTION OPPORTUNITIES")
    print("-" * 40)
    
    opportunities = identify_opportunities(csv_stats, api_stats, atlas_stats)
    
    # 5. Generate extraction strategy
    print("\n🚀 STEP 5: RECOMMENDED EXTRACTION STRATEGY")
    print("-" * 40)
    
    generate_extraction_strategy(opportunities)
    
    return {
        'csv_stats': csv_stats,
        'api_stats': api_stats,
        'atlas_stats': atlas_stats,
        'opportunities': opportunities
    }

def analyze_csv_source(csv_file):
    """Analyze the source CSV export comprehensively"""
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return {}
    
    stats = {
        'total_items': 0,
        'web_urls': 0,
        'private_content': 0,
        'with_selection': 0,
        'folders': defaultdict(int),
        'years': defaultdict(int),
        'selection_lengths': []
    }
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                stats['total_items'] += 1
                
                url = row.get('URL', '').strip()
                selection = row.get('Selection', '').strip()
                folder = row.get('Folder', 'Unknown')
                timestamp = row.get('Timestamp', '').strip()
                
                # URL categorization
                if url.startswith('http'):
                    stats['web_urls'] += 1
                elif url.startswith('instapaper-private://'):
                    stats['private_content'] += 1
                
                # Selection content
                if selection:
                    stats['with_selection'] += 1
                    stats['selection_lengths'].append(len(selection))
                
                # Folder distribution
                stats['folders'][folder] += 1
                
                # Time analysis
                if timestamp.isdigit():
                    try:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(int(timestamp))
                        year = dt.year
                        stats['years'][year] += 1
                    except:
                        pass
    
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")
        return {}
    
    print(f"  Total items in CSV: {stats['total_items']:,}")
    print(f"  Web URLs: {stats['web_urls']:,}")
    print(f"  Private content: {stats['private_content']:,}")
    print(f"  Items with selection content: {stats['with_selection']:,}")
    
    if stats['selection_lengths']:
        avg_selection = sum(stats['selection_lengths']) / len(stats['selection_lengths'])
        print(f"  Average selection length: {avg_selection:.0f} chars")
    
    print(f"  Folders: {len(stats['folders'])}")
    for folder, count in sorted(stats['folders'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {folder}: {count:,} items")
    
    print(f"  Year range: {min(stats['years'].keys()) if stats['years'] else 'N/A'} - {max(stats['years'].keys()) if stats['years'] else 'N/A'}")
    
    return stats

def analyze_api_extractions():
    """Analyze what we've extracted via API so far"""
    
    stats = {
        'private_batches': 0,
        'total_private_extracted': 0,
        'total_private_attempted': 0,
        'success_rates': [],
        'content_lengths': []
    }
    
    # Analyze private newsletter extractions
    batch_files = glob.glob('private_newsletter_batch_*.json')
    
    if batch_files:
        print(f"  Private newsletter batches found: {len(batch_files)}")
        
        for batch_file in sorted(batch_files):
            try:
                with open(batch_file, 'r') as f:
                    batch_data = json.load(f)
                
                successful = batch_data.get('successful_extractions', 0)
                failed = batch_data.get('failed_extractions', 0)
                total_batch = successful + failed
                
                stats['private_batches'] += 1
                stats['total_private_extracted'] += successful
                stats['total_private_attempted'] += total_batch
                
                if total_batch > 0:
                    success_rate = successful / total_batch * 100
                    stats['success_rates'].append(success_rate)
                
                # Analyze content lengths
                extracted_content = batch_data.get('extracted_content', {})
                for content_data in extracted_content.values():
                    length = content_data.get('content_length', 0)
                    if length > 0:
                        stats['content_lengths'].append(length)
                
                start_idx = batch_data.get('start_index', 0)
                end_idx = batch_data.get('end_index', 0)
                print(f"    Batch {start_idx}-{end_idx}: {successful}/{total_batch} success ({success_rate:.1f}%)")
                
            except Exception as e:
                print(f"    Error reading {batch_file}: {e}")
    
    else:
        print("  No private newsletter batch files found")
    
    print(f"  Total private newsletters extracted: {stats['total_private_extracted']:,}")
    
    if stats['success_rates']:
        avg_success = sum(stats['success_rates']) / len(stats['success_rates'])
        print(f"  Average success rate: {avg_success:.1f}%")
    
    if stats['content_lengths']:
        avg_length = sum(stats['content_lengths']) / len(stats['content_lengths'])
        print(f"  Average content length: {avg_length:,.0f} chars")
    
    return stats

def analyze_atlas_collection():
    """Analyze current Atlas collection"""
    
    stats = {
        'total_html_files': 0,
        'total_md_files': 0,
        'total_metadata_files': 0
    }
    
    # Count files in Atlas directories
    html_dir = "output/articles/html"
    md_dir = "output/articles/markdown"
    metadata_dir = "output/articles/metadata"
    
    if os.path.exists(html_dir):
        stats['total_html_files'] = len([f for f in os.listdir(html_dir) if f.endswith('.html')])
    
    if os.path.exists(md_dir):
        stats['total_md_files'] = len([f for f in os.listdir(md_dir) if f.endswith('.md')])
    
    if os.path.exists(metadata_dir):
        stats['total_metadata_files'] = len([f for f in os.listdir(metadata_dir) if f.endswith('.json')])
    
    print(f"  HTML files: {stats['total_html_files']:,}")
    print(f"  Markdown files: {stats['total_md_files']:,}")
    print(f"  Metadata files: {stats['total_metadata_files']:,}")
    
    return stats

def identify_opportunities(csv_stats, api_stats, atlas_stats):
    """Identify remaining extraction opportunities"""
    
    opportunities = []
    
    # 1. Remaining private newsletters
    total_private_in_csv = csv_stats.get('private_content', 0)
    extracted_private = api_stats.get('total_private_extracted', 0)
    
    if total_private_in_csv > extracted_private:
        remaining_private = total_private_in_csv - extracted_private
        opportunities.append({
            'type': 'remaining_private_newsletters',
            'count': remaining_private,
            'description': f'{remaining_private:,} private newsletters not yet extracted via API',
            'priority': 'high'
        })
    
    # 2. API continuation opportunity
    if api_stats.get('total_private_attempted', 0) < 393:  # We know API has 393 private items
        remaining_api = 393 - api_stats.get('total_private_attempted', 0)
        opportunities.append({
            'type': 'continue_api_extraction',
            'count': remaining_api,
            'description': f'{remaining_api} private newsletters found in API but not yet extracted',
            'priority': 'high'
        })
    
    # 3. CSV Selection content not utilized
    csv_with_selection = csv_stats.get('with_selection', 0)
    if csv_with_selection > 0:
        opportunities.append({
            'type': 'csv_selection_content',
            'count': csv_with_selection,
            'description': f'{csv_with_selection:,} CSV items have Selection content that could be better utilized',
            'priority': 'medium'
        })
    
    # 4. Web URLs for Atlas pipeline
    web_urls = csv_stats.get('web_urls', 0)
    opportunities.append({
        'type': 'web_urls_for_atlas',
        'count': web_urls,
        'description': f'{web_urls:,} web URLs ready for Atlas content fetching pipeline',
        'priority': 'low'
    })
    
    print(f"  🎯 Identified {len(opportunities)} extraction opportunities:")
    for opp in opportunities:
        priority_icon = "🔥" if opp['priority'] == 'high' else "⚡" if opp['priority'] == 'medium' else "💡"
        print(f"    {priority_icon} {opp['description']}")
    
    return opportunities

def generate_extraction_strategy(opportunities):
    """Generate recommended extraction strategy"""
    
    high_priority = [o for o in opportunities if o['priority'] == 'high']
    
    if high_priority:
        print("  🔥 HIGH PRIORITY ACTIONS:")
        
        for opp in high_priority:
            if opp['type'] == 'continue_api_extraction':
                print(f"    1. Continue private newsletter API extraction")
                print(f"       - Resume from item {150} (we extracted 0-149)")
                print(f"       - Target: Extract {opp['count']} more newsletters")
                print(f"       - Expected: ~{opp['count'] * 30000:,} more characters of content")
                print(f"       - Command: python3 extract_private_newsletters_resumable.py 150")
            
            elif opp['type'] == 'remaining_private_newsletters':
                print(f"    2. Investigate historical private content access")
                print(f"       - CSV shows {opp['count']:,} total private items")
                print(f"       - API only provides recent ~393 items")  
                print(f"       - Need alternative approach for historical newsletters")
    
    print(f"\n  ⚡ MEDIUM PRIORITY:")
    print(f"    - Optimize CSV Selection content extraction")
    print(f"    - Improve content quality detection algorithms")
    
    print(f"\n  💡 LOW PRIORITY (Atlas Pipeline):")
    print(f"    - Process web URLs through Atlas content fetching")
    print(f"    - Integrate with main Atlas processing workflow")

if __name__ == '__main__':
    results = analyze_extraction_status()
    
    print(f"\n🎯 SUMMARY:")
    print(f"=" * 60)
    
    csv_total = results['csv_stats'].get('total_items', 0)
    atlas_total = results['atlas_stats'].get('total_html_files', 0)
    
    print(f"📊 Source CSV: {csv_total:,} total items")
    print(f"📁 Atlas collection: {atlas_total:,} files")
    print(f"📈 Extraction coverage: {atlas_total/csv_total*100:.1f}%" if csv_total > 0 else "0%")
    
    high_priority_count = len([o for o in results['opportunities'] if o['priority'] == 'high'])
    print(f"🎯 High priority opportunities: {high_priority_count}")
    
    if high_priority_count > 0:
        print(f"\n🚀 NEXT STEPS: Focus on high priority opportunities to maximize content extraction!")