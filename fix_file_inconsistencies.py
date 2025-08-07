#!/usr/bin/env python3
"""
Fix file inconsistencies - align HTML/MD/metadata files
"""

import os
import json
import shutil
from datetime import datetime

def fix_file_inconsistencies():
    """Fix the mismatch between HTML/MD/metadata files"""
    
    print("🔧 FIXING FILE INCONSISTENCIES")
    print("=" * 50)
    
    # Get all file sets
    html_files = set([f.replace('.html', '') for f in os.listdir('output/articles/html') if f.endswith('.html')])
    md_files = set([f.replace('.md', '') for f in os.listdir('output/articles/markdown') if f.endswith('.md')])  
    metadata_files = set([f.replace('.json', '') for f in os.listdir('output/articles/metadata') if f.endswith('.json')])
    
    print(f"📊 Current file counts:")
    print(f"  HTML files: {len(html_files):,}")
    print(f"  Markdown files: {len(md_files):,}")
    print(f"  Metadata files: {len(metadata_files):,}")
    
    # Find mismatches
    only_metadata = metadata_files - html_files - md_files
    only_html = html_files - metadata_files
    only_md = md_files - metadata_files
    
    print(f"\n🔍 Mismatches identified:")
    print(f"  Metadata without HTML/MD: {len(only_metadata)}")
    print(f"  HTML without metadata: {len(only_html)}")
    print(f"  MD without metadata: {len(only_md)}")
    
    # Create inconsistencies directory
    inconsist_dir = "file_inconsistencies"
    os.makedirs(f"{inconsist_dir}/orphaned_metadata", exist_ok=True)
    os.makedirs(f"{inconsist_dir}/orphaned_html", exist_ok=True)
    os.makedirs(f"{inconsist_dir}/orphaned_md", exist_ok=True)
    
    # Analyze and move orphaned metadata files
    moved_metadata = 0
    analyzed_orphans = []
    
    if only_metadata:
        print(f"\n🔄 Analyzing orphaned metadata files...")
        
        for uid in only_metadata:
            try:
                metadata_path = f"output/articles/metadata/{uid}.json"
                
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Analyze why this is orphaned
                source = metadata.get('source', '')
                title = metadata.get('title', '')
                content_type = metadata.get('content_type', '')
                fetch_method = metadata.get('fetch_method', '')
                
                orphan_reason = "unknown"
                
                # Categorize reason
                if 'instapaper://private-content/' in source:
                    orphan_reason = "private_content_placeholder"
                elif source == 'about:blank':
                    orphan_reason = "blank_url"
                elif not source or source.strip() == '':
                    orphan_reason = "empty_url"
                elif 'login' in title.lower() or 'error' in title.lower():
                    orphan_reason = "error_page"
                else:
                    orphan_reason = "processing_failure"
                
                analyzed_orphans.append({
                    'uid': uid,
                    'title': title[:60] + "..." if len(title) > 60 else title,
                    'source': source,
                    'content_type': content_type,
                    'reason': orphan_reason
                })
                
                # Move to inconsistencies folder
                shutil.move(metadata_path, f"{inconsist_dir}/orphaned_metadata/{uid}.json")
                moved_metadata += 1
                
                if moved_metadata % 50 == 0:
                    print(f"    Moved {moved_metadata} orphaned metadata files...")
                
            except Exception as e:
                print(f"    ❌ Error processing {uid}: {e}")
    
    # Move orphaned HTML files
    moved_html = 0
    for uid in only_html:
        try:
            html_path = f"output/articles/html/{uid}.html"
            shutil.move(html_path, f"{inconsist_dir}/orphaned_html/{uid}.html")
            moved_html += 1
        except Exception as e:
            print(f"    ❌ Error moving HTML {uid}: {e}")
    
    # Move orphaned MD files
    moved_md = 0
    for uid in only_md:
        try:
            md_path = f"output/articles/markdown/{uid}.md"
            shutil.move(md_path, f"{inconsist_dir}/orphaned_md/{uid}.md")
            moved_md += 1
        except Exception as e:
            print(f"    ❌ Error moving MD {uid}: {e}")
    
    print(f"\n✅ INCONSISTENCY CLEANUP COMPLETE!")
    print(f"  📁 Moved to {inconsist_dir}/:")
    print(f"    Orphaned metadata: {moved_metadata}")
    print(f"    Orphaned HTML: {moved_html}")
    print(f"    Orphaned MD: {moved_md}")
    
    # Verify file alignment
    print(f"\n🔍 Verifying file alignment...")
    
    html_files_after = set([f.replace('.html', '') for f in os.listdir('output/articles/html') if f.endswith('.html')])
    md_files_after = set([f.replace('.md', '') for f in os.listdir('output/articles/markdown') if f.endswith('.md')])  
    metadata_files_after = set([f.replace('.json', '') for f in os.listdir('output/articles/metadata') if f.endswith('.json')])
    
    print(f"  📊 Final aligned counts:")
    print(f"    HTML files: {len(html_files_after):,}")
    print(f"    Markdown files: {len(md_files_after):,}")
    print(f"    Metadata files: {len(metadata_files_after):,}")
    
    # Check alignment
    if len(html_files_after) == len(md_files_after) == len(metadata_files_after):
        print(f"  ✅ Files are now perfectly aligned!")
        alignment_status = "perfect"
    else:
        remaining_mismatches = abs(len(html_files_after) - len(metadata_files_after))
        print(f"  ⚠️  Still {remaining_mismatches} mismatches remaining")
        alignment_status = f"{remaining_mismatches}_mismatches_remain"
    
    # Analyze orphan reasons
    print(f"\n📊 ORPHANED METADATA ANALYSIS:")
    
    reason_counts = {}
    for orphan in analyzed_orphans:
        reason = orphan['reason']
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    
    for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason.replace('_', ' ').title()}: {count}")
    
    # Show samples
    if analyzed_orphans:
        print(f"\n🔍 Sample orphaned files:")
        for i, orphan in enumerate(analyzed_orphans[:5]):
            print(f"  {i+1}. {orphan['reason']}: {orphan['title']}")
            print(f"     Source: {orphan['source']}")
    
    # Create report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    report = {
        'cleanup_timestamp': timestamp,
        'original_counts': {
            'html': len(html_files),
            'md': len(md_files),
            'metadata': len(metadata_files)
        },
        'final_counts': {
            'html': len(html_files_after),
            'md': len(md_files_after),
            'metadata': len(metadata_files_after)
        },
        'moved_files': {
            'orphaned_metadata': moved_metadata,
            'orphaned_html': moved_html,
            'orphaned_md': moved_md
        },
        'alignment_status': alignment_status,
        'orphan_reasons': reason_counts,
        'sample_orphans': analyzed_orphans[:10]
    }
    
    report_file = f"file_inconsistency_cleanup_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Cleanup report saved: {report_file}")
    
    return {
        'final_aligned_count': len(metadata_files_after),
        'alignment_status': alignment_status,
        'orphans_moved': moved_metadata + moved_html + moved_md
    }

if __name__ == '__main__':
    fix_file_inconsistencies()