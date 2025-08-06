#!/usr/bin/env python3
"""
Clean up junk articles - identify and move/delete useless stub articles
"""

import os
import json
import shutil
from datetime import datetime

def cleanup_junk_articles():
    """Identify and clean up junk articles with no real content"""
    
    print("🗑️  CLEANING UP JUNK ARTICLES")
    print("=" * 50)
    
    # Directories
    atlas_dirs = {
        'html': 'output/articles/html',
        'markdown': 'output/articles/markdown',
        'metadata': 'output/articles/metadata'
    }
    
    # Create junk directory
    junk_dir = 'junk_articles'
    junk_dirs = {
        'html': f'{junk_dir}/html',
        'markdown': f'{junk_dir}/markdown', 
        'metadata': f'{junk_dir}/metadata'
    }
    
    for directory in junk_dirs.values():
        os.makedirs(directory, exist_ok=True)
    
    print(f"📁 Created junk directory: {junk_dir}/")
    
    # Analyze all metadata files to identify junk
    print(f"\n🔍 Analyzing articles for junk content...")
    
    junk_criteria = {
        'about_blank': 0,
        'no_content_message': 0,
        'minimal_content': 0,
        'invalid_urls': 0,
        'other_junk': 0
    }
    
    junk_files = []
    quality_files = []
    
    metadata_dir = atlas_dirs['metadata']
    if not os.path.exists(metadata_dir):
        print(f"❌ Metadata directory not found: {metadata_dir}")
        return
    
    metadata_files = [f for f in os.listdir(metadata_dir) if f.endswith('.json')]
    print(f"  📊 Analyzing {len(metadata_files):,} articles...")
    
    for metadata_file in metadata_files:
        try:
            uid = metadata_file.replace('.json', '')
            metadata_path = os.path.join(metadata_dir, metadata_file)
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            source = metadata.get('source', '')
            title = metadata.get('title', '')
            content_type = metadata.get('content_type', '')
            
            # Check if it's junk
            is_junk = False
            junk_reason = ''
            
            # 1. about:blank URLs
            if source == 'about:blank':
                is_junk = True
                junk_reason = 'about_blank'
                junk_criteria['about_blank'] += 1
            
            # 2. Check markdown content for "Content would need to be fetched"
            elif check_has_fetch_message(uid, atlas_dirs['markdown']):
                is_junk = True
                junk_reason = 'no_content_message'
                junk_criteria['no_content_message'] += 1
            
            # 3. Invalid/empty URLs
            elif not source or source.strip() == '' or source == 'unknown':
                is_junk = True
                junk_reason = 'invalid_urls'
                junk_criteria['invalid_urls'] += 1
            
            # 4. Check for minimal content (very short titles, no useful info)
            elif is_minimal_content(metadata, uid, atlas_dirs['markdown']):
                is_junk = True
                junk_reason = 'minimal_content'
                junk_criteria['minimal_content'] += 1
            
            if is_junk:
                junk_files.append({
                    'uid': uid,
                    'reason': junk_reason,
                    'source': source,
                    'title': title[:50] + "..." if len(title) > 50 else title
                })
            else:
                quality_files.append(uid)
                
        except Exception as e:
            print(f"    ❌ Error analyzing {metadata_file}: {e}")
            continue
    
    print(f"\n📊 ANALYSIS RESULTS:")
    print(f"  🗑️  Junk articles found: {len(junk_files):,}")
    print(f"  ✅ Quality articles: {len(quality_files):,}")
    print(f"  📈 Quality percentage: {len(quality_files)/(len(junk_files)+len(quality_files))*100:.1f}%")
    
    print(f"\n🗑️  JUNK BREAKDOWN:")
    for reason, count in junk_criteria.items():
        if count > 0:
            reason_name = reason.replace('_', ' ').title()
            print(f"    {reason_name}: {count:,} articles")
    
    # Show some examples
    print(f"\n🔍 SAMPLE JUNK ARTICLES:")
    for i, junk in enumerate(junk_files[:5]):
        print(f"    {i+1}. {junk['reason']}: {junk['title']}")
        print(f"       Source: {junk['source']}")
    
    if len(junk_files) > 5:
        print(f"    ... and {len(junk_files)-5:,} more")
    
    # Auto-proceed with cleanup
    print(f"\n✅ AUTO-PROCEEDING WITH CLEANUP")
    print(f"  Will move {len(junk_files):,} junk articles to {junk_dir}/")
    print(f"  Will keep {len(quality_files):,} quality articles in main collection")
    
    # Move junk files
    print(f"\n🔄 Moving junk articles...")
    
    moved_count = 0
    for junk in junk_files:
        uid = junk['uid']
        
        try:
            # Move HTML file
            html_src = f"{atlas_dirs['html']}/{uid}.html"
            html_dst = f"{junk_dirs['html']}/{uid}.html"
            if os.path.exists(html_src):
                shutil.move(html_src, html_dst)
            
            # Move Markdown file
            md_src = f"{atlas_dirs['markdown']}/{uid}.md"
            md_dst = f"{junk_dirs['markdown']}/{uid}.md"
            if os.path.exists(md_src):
                shutil.move(md_src, md_dst)
            
            # Move Metadata file
            meta_src = f"{atlas_dirs['metadata']}/{uid}.json"
            meta_dst = f"{junk_dirs['metadata']}/{uid}.json"
            if os.path.exists(meta_src):
                shutil.move(meta_src, meta_dst)
            
            moved_count += 1
            
            if moved_count % 1000 == 0:
                print(f"    ✅ Moved {moved_count:,} articles...")
            
        except Exception as e:
            print(f"    ❌ Error moving {uid}: {e}")
    
    print(f"\n🎯 CLEANUP COMPLETE!")
    print(f"  ✅ Moved {moved_count:,} junk articles to {junk_dir}/")
    print(f"  🏆 Remaining quality articles: {len(quality_files):,}")
    
    # Create cleanup report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report = {
        'cleanup_timestamp': timestamp,
        'junk_articles_moved': moved_count,
        'quality_articles_remaining': len(quality_files),
        'junk_breakdown': junk_criteria,
        'cleanup_directory': junk_dir,
        'sample_junk_files': junk_files[:20]  # Save some examples
    }
    
    report_file = f"junk_cleanup_report_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"  📄 Cleanup report: {report_file}")
    
    # Final status
    print(f"\n📊 FINAL ATLAS COLLECTION STATUS:")
    
    # Count remaining files
    remaining_html = len([f for f in os.listdir(atlas_dirs['html']) if f.endswith('.html')])
    remaining_md = len([f for f in os.listdir(atlas_dirs['markdown']) if f.endswith('.md')])
    remaining_meta = len([f for f in os.listdir(atlas_dirs['metadata']) if f.endswith('.json')])
    
    print(f"  📁 Quality Articles Remaining:")
    print(f"    HTML files: {remaining_html:,}")
    print(f"    Markdown files: {remaining_md:,}")
    print(f"    Metadata files: {remaining_meta:,}")
    
    print(f"\n✨ Your Atlas collection is now clean and focused on quality content!")

def check_has_fetch_message(uid, markdown_dir):
    """Check if markdown file has 'Content would need to be fetched' message"""
    
    md_path = f"{markdown_dir}/{uid}.md"
    if not os.path.exists(md_path):
        return False
    
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fetch_indicators = [
            'Content would need to be fetched separately',
            '*Content would need to be fetched',
            'would need to be fetched separately for web URLs'
        ]
        
        return any(indicator in content for indicator in fetch_indicators)
        
    except Exception as e:
        return False

def is_minimal_content(metadata, uid, markdown_dir):
    """Check if article has minimal/useless content"""
    
    title = metadata.get('title', '')
    source = metadata.get('source', '')
    
    # Check for generic/empty titles
    generic_titles = [
        'untitled',
        'no title', 
        'login',
        'error',
        'page not found',
        '404',
        'access denied',
        'redirect',
        '',
        ' '
    ]
    
    if title.lower().strip() in generic_titles:
        return True
    
    # Check markdown file size/content
    md_path = f"{markdown_dir}/{uid}.md"
    if os.path.exists(md_path):
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Very short content (likely just metadata)
            if len(content.strip()) < 200:
                return True
            
            # Count actual content lines (not metadata)
            content_lines = [line for line in content.split('\n') 
                           if line.strip() and not line.startswith('**') and not line.startswith('#')]
            
            if len(' '.join(content_lines).strip()) < 100:
                return True
                
        except:
            pass
    
    return False

if __name__ == '__main__':
    cleanup_junk_articles()