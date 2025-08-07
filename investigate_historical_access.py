#!/usr/bin/env python3
"""
Investigate historical content access methods for private newsletters
"""

import os
import csv
import json
from collections import defaultdict
from datetime import datetime

def investigate_historical_access():
    """Analyze historical private content access opportunities"""
    
    print("🔍 INVESTIGATING HISTORICAL CONTENT ACCESS")
    print("=" * 60)
    
    csv_file = "inputs/instapaper_export.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    print("📊 ANALYZING PRIVATE CONTENT IN CSV...")
    print("-" * 40)
    
    private_analysis = {
        'total_private': 0,
        'with_selection': 0,
        'without_selection': 0,
        'selection_lengths': [],
        'years': defaultdict(int),
        'sources': defaultdict(int),
        'sample_entries': []
    }
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                url = row.get('URL', '').strip()
                
                # Focus on private content
                if url.startswith('instapaper-private://'):
                    private_analysis['total_private'] += 1
                    
                    selection = row.get('Selection', '').strip()
                    title = row.get('Title', 'Untitled')
                    timestamp = row.get('Timestamp', '').strip()
                    
                    # Analyze selection content
                    if selection and len(selection) > 100:  # Substantial selection
                        private_analysis['with_selection'] += 1
                        private_analysis['selection_lengths'].append(len(selection))
                        
                        # Sample entry
                        if len(private_analysis['sample_entries']) < 5:
                            private_analysis['sample_entries'].append({
                                'title': title,
                                'selection_length': len(selection),
                                'selection_preview': selection[:200] + "..." if len(selection) > 200 else selection,
                                'url': url
                            })
                    else:
                        private_analysis['without_selection'] += 1
                    
                    # Time analysis
                    if timestamp.isdigit():
                        try:
                            dt = datetime.fromtimestamp(int(timestamp))
                            year = dt.year
                            private_analysis['years'][year] += 1
                        except:
                            pass
                    
                    # Source analysis (extract from private URL)
                    if 'instapaper-private://' in url:
                        # Try to extract source identifier
                        source_part = url.replace('instapaper-private://', '')
                        if '/' in source_part:
                            source = source_part.split('/')[0]
                            private_analysis['sources'][source] += 1
    
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")
        return
    
    # Report findings
    print(f"📊 PRIVATE CONTENT ANALYSIS:")
    print(f"  Total private items in CSV: {private_analysis['total_private']:,}")
    print(f"  Items with substantial selection content: {private_analysis['with_selection']:,}")
    print(f"  Items without selection content: {private_analysis['without_selection']:,}")
    print(f"  Selection content coverage: {private_analysis['with_selection']/private_analysis['total_private']*100:.1f}%")
    
    if private_analysis['selection_lengths']:
        avg_selection = sum(private_analysis['selection_lengths']) / len(private_analysis['selection_lengths'])
        max_selection = max(private_analysis['selection_lengths'])
        print(f"  Average selection length: {avg_selection:,.0f} chars")
        print(f"  Maximum selection length: {max_selection:,} chars")
        total_selection_chars = sum(private_analysis['selection_lengths'])
        print(f"  Total selection content: {total_selection_chars:,} chars")
    
    print(f"\n📅 TEMPORAL DISTRIBUTION:")
    sorted_years = sorted(private_analysis['years'].items())
    for year, count in sorted_years:
        print(f"  {year}: {count:,} private items")
    
    print(f"\n📡 TOP SOURCES:")
    top_sources = sorted(private_analysis['sources'].items(), key=lambda x: x[1], reverse=True)[:10]
    for source, count in top_sources:
        print(f"  {source}: {count:,} items")
    
    print(f"\n🔍 SAMPLE ENTRIES WITH SELECTION CONTENT:")
    for i, entry in enumerate(private_analysis['sample_entries'], 1):
        print(f"  {i}. {entry['title'][:60]}...")
        print(f"     Selection length: {entry['selection_length']:,} chars")
        print(f"     Preview: {entry['selection_preview']}")
        print()
    
    # Analyze extraction potential
    print(f"📈 EXTRACTION POTENTIAL:")
    print("-" * 40)
    
    api_accessible = 137  # What we successfully extracted via API
    csv_with_content = private_analysis['with_selection']
    
    print(f"  ✅ API accessible (already extracted): {api_accessible:,} items")
    print(f"  📄 CSV Selection content available: {csv_with_content:,} items")
    
    if csv_with_content > api_accessible:
        additional_via_csv = csv_with_content - api_accessible
        print(f"  🎯 Additional content via CSV Selection: {additional_via_csv:,} items")
        
        if private_analysis['selection_lengths']:
            estimated_additional_chars = additional_via_csv * avg_selection
            print(f"  📊 Estimated additional content: {estimated_additional_chars:,} chars")
    
    # Recommendations
    print(f"\n🚀 RECOMMENDATIONS:")
    print("-" * 40)
    
    if private_analysis['with_selection'] > 0:
        print(f"  1. 🔥 HIGH PRIORITY: Extract CSV Selection content")
        print(f"     - {private_analysis['with_selection']:,} private items have selection content")
        print(f"     - This could significantly increase our private newsletter collection")
        print(f"     - Selection content is often substantial (avg {avg_selection:,.0f} chars)")
    
    print(f"  2. ⚡ MEDIUM PRIORITY: Improve Selection extraction algorithm")
    print(f"     - Current content quality analyzer may not be fully utilizing Selection data")
    print(f"     - Could enhance extraction from existing {private_analysis['total_private']:,} private items")
    
    print(f"  3. 💡 LOW PRIORITY: Investigate alternative access methods")
    print(f"     - Historical private content beyond API limitations")
    print(f"     - {private_analysis['without_selection']:,} private items have no selection content")
    
    return private_analysis

if __name__ == '__main__':
    results = investigate_historical_access()