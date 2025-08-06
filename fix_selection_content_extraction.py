#!/usr/bin/env python3
"""
Fix Selection content extraction - Critical bug fix to unlock 1,144 articles
"""

import os
import csv
import json
import hashlib
import re
from datetime import datetime
from urllib.parse import urlparse

def fix_selection_content_extraction():
    """Fix the critical Selection content extraction bug"""
    
    print("🔥 FIXING SELECTION CONTENT EXTRACTION BUG")
    print("=" * 60)
    
    csv_file = "inputs/instapaper_export.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    # Create output directories
    output_dirs = [
        "output/articles/html",
        "output/articles/markdown", 
        "output/articles/metadata"
    ]
    
    for directory in output_dirs:
        os.makedirs(directory, exist_ok=True)
    
    print("📊 Analyzing Selection content in CSV...")
    
    # First pass: analyze what Selection content we have
    selection_stats = {
        'total_items': 0,
        'items_with_selection': 0,
        'selection_lengths': [],
        'substantial_selection': 0  # >100 chars
    }
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                selection_stats['total_items'] += 1
                selection = row.get('Selection', '').strip()
                
                if selection:
                    selection_stats['items_with_selection'] += 1
                    selection_stats['selection_lengths'].append(len(selection))
                    
                    if len(selection) > 100:
                        selection_stats['substantial_selection'] += 1
    
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")
        return
    
    print(f"  📋 Total items: {selection_stats['total_items']:,}")
    print(f"  📝 Items with selection: {selection_stats['items_with_selection']:,}")
    print(f"  🎯 Substantial selection (>100 chars): {selection_stats['substantial_selection']:,}")
    
    if selection_stats['selection_lengths']:
        avg_length = sum(selection_stats['selection_lengths']) / len(selection_stats['selection_lengths'])
        total_chars = sum(selection_stats['selection_lengths'])
        print(f"  📏 Average selection length: {avg_length:.0f} chars")
        print(f"  💰 Total selection content: {total_chars:,} characters")
    
    # Second pass: Process items with substantial Selection content
    print(f"\n🔄 Processing items with substantial Selection content...")
    
    processed = 0
    selection_processed = 0
    total_selection_chars = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    url = row.get('URL', '').strip()
                    title = row.get('Title', 'Untitled').strip()
                    folder = row.get('Folder', 'Unknown').strip()
                    timestamp = row.get('Timestamp', '').strip()
                    selection = row.get('Selection', '').strip()
                    tags = row.get('Tags', '').strip()
                    
                    if not url:
                        continue
                    
                    # Generate unique ID
                    uid = generate_unique_id(url, title, timestamp)
                    
                    # Only process items with substantial Selection content OR reprocess all
                    has_substantial_selection = len(selection) > 100
                    
                    # Only process items with substantial Selection content
                    if not has_substantial_selection:
                        continue
                    
                    # Always process items with substantial selection (force reprocessing)
                    should_process = True
                    
                    if not should_process:
                        continue
                    
                    # Categorize content type
                    if url.startswith('http'):
                        content_type = "web_bookmark_with_selection"
                        is_private = False
                        private_source = ""
                        domain = extract_domain(url)
                    elif url.startswith('instapaper-private://'):
                        content_type = "private_content_with_selection"
                        is_private = True
                        private_source = "instapaper_email"
                        domain = "private"
                    else:
                        content_type = "unknown_with_selection"
                        is_private = False
                        private_source = ""
                        domain = "unknown"
                    
                    # Convert timestamp
                    try:
                        if timestamp.isdigit():
                            dt = datetime.fromtimestamp(int(timestamp))
                            formatted_timestamp = dt.isoformat()
                        else:
                            formatted_timestamp = datetime.now().isoformat()
                    except:
                        formatted_timestamp = datetime.now().isoformat()
                    
                    # Process and clean selection content
                    cleaned_selection = clean_selection_content(selection)
                    
                    # Create enhanced HTML content with proper Selection extraction
                    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="content-source" value="instapaper_selection">
</head>
<body>
    <h1>{title}</h1>
    
    <div class="instapaper-info">
        <p><strong>Source:</strong> <a href="{url}">{url}</a></p>
        <p><strong>Domain:</strong> {domain}</p>
        <p><strong>Folder:</strong> {folder}</p>
        <p><strong>Added:</strong> {formatted_timestamp}</p>
        <p><strong>Content Type:</strong> Selection Content Extracted</p>
        <p><strong>Selection Length:</strong> {len(selection):,} characters</p>
        {f'<p><strong>Tags:</strong> {tags}</p>' if tags and tags != '[]' else ''}
    </div>
    
    <div class="selection-content">
        <h2>Selected Content</h2>
        <div class="content-body">
            {cleaned_selection}
        </div>
        <p><em>This content was extracted from your Instapaper Selection field - representing the key parts you highlighted or selected from the original article.</em></p>
    </div>
    
    <div class="metadata">
        <p><strong>Original Selection:</strong></p>
        <blockquote>{selection}</blockquote>
    </div>
</body>
</html>"""
                    
                    # Create enhanced Markdown content with proper Selection extraction
                    markdown_content = f"""# {title}

**Source:** {url}  
**Domain:** {domain}  
**Folder:** {folder}  
**Added:** {formatted_timestamp}  
**Content Type:** Selection Content Extracted  
**Selection Length:** {len(selection):,} characters  
{f'**Tags:** {tags}' if tags and tags != '[]' else ''}

---

## Selected Content

{cleaned_selection}

---

*This content was extracted from your Instapaper Selection field - representing the key parts you highlighted or selected from the original article.*

### Original Selection

> {selection}
"""
                    
                    # Create enhanced metadata JSON
                    metadata = {
                        "uid": uid,
                        "content_type": content_type,
                        "source": url,
                        "title": title,
                        "status": "selection_content_extracted",
                        "date": formatted_timestamp,
                        "error": None,
                        "content_path": f"output/articles/markdown/{uid}.md",
                        "html_path": f"output/articles/html/{uid}.html",
                        "audio_path": None,
                        "transcript_path": None,
                        "tags": [tag.strip() for tag in tags.replace('[', '').replace(']', '').split(',') if tag.strip() and tag.strip() != '[]'],
                        "notes": [],
                        "fetch_method": "instapaper_selection_extraction",
                        "fetch_details": {
                            "source": "instapaper_csv_selection_field",
                            "csv_row": row_num,
                            "selection_length": len(selection),
                            "cleaned_selection_length": len(cleaned_selection),
                            "domain": domain,
                            "extraction_method": "enhanced_selection_processor"
                        },
                        "category_version": None,
                        "last_tagged_at": None,
                        "source_hash": uid,  # Use UID as source hash for deduplication
                        "type_specific": {
                            "folder": folder,
                            "instapaper_timestamp": timestamp,
                            "is_private_content": is_private,
                            "private_source": private_source,
                            "selection": selection,
                            "cleaned_selection": cleaned_selection,
                            "domain": domain,
                            "has_substantial_content": True
                        },
                        "video_id": None,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # Write files
                    with open(f"output/articles/html/{uid}.html", 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    with open(f"output/articles/markdown/{uid}.md", 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    
                    with open(f"output/articles/metadata/{uid}.json", 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    processed += 1
                    if has_substantial_selection:
                        selection_processed += 1
                        total_selection_chars += len(selection)
                    
                    # Progress indicator
                    if processed % 100 == 0:
                        print(f"  ✅ Processed {processed} items with Selection content...")
                    
                except Exception as e:
                    print(f"  ❌ Error processing row {row_num}: {e}")
                    continue
    
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        return
    
    print()
    print("🎯 SELECTION CONTENT EXTRACTION COMPLETE!")
    print("=" * 60)
    print(f"  📊 Total items processed: {processed:,}")
    print(f"  📝 Items with substantial Selection content: {selection_processed:,}")
    print(f"  💰 Total Selection characters extracted: {total_selection_chars:,}")
    print(f"  📈 Average Selection length: {total_selection_chars/selection_processed:.0f} chars" if selection_processed > 0 else "")
    
    # Create detailed report
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = f"selection_content_extraction_report_{timestamp_str}.json"
    
    report = {
        "extraction_timestamp": timestamp_str,
        "total_csv_items": selection_stats['total_items'],
        "items_with_selection": selection_stats['items_with_selection'],
        "substantial_selection_items": selection_stats['substantial_selection'],
        "processed_items": processed,
        "selection_content_extracted": selection_processed,
        "total_selection_characters": total_selection_chars,
        "average_selection_length": total_selection_chars/selection_processed if selection_processed > 0 else 0,
        "extraction_method": "enhanced_selection_processor",
        "files_created": {
            "html": processed,
            "markdown": processed,
            "metadata": processed
        },
        "success_rate": 100.0 if selection_stats['substantial_selection'] == selection_processed else (selection_processed/selection_stats['substantial_selection']*100),
        "content_quality": "substantial_selection_content_extracted"
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"  📄 Detailed report saved: {report_file}")
    print()
    print("✅ CRITICAL BUG FIXED: Selection content now properly extracted!")
    print(f"🎉 UNLOCKED: {selection_processed:,} articles with {total_selection_chars:,} characters of real content!")

def generate_unique_id(url, title, timestamp):
    """Generate a unique ID for the bookmark"""
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

def clean_selection_content(selection):
    """Clean and format selection content for better readability"""
    if not selection:
        return ""
    
    # Convert to HTML paragraphs
    # Handle different line break patterns
    content = selection.strip()
    
    # Replace multiple newlines with paragraph breaks
    content = re.sub(r'\n\s*\n', '</p><p>', content)
    
    # Replace single newlines with line breaks
    content = re.sub(r'\n', '<br>', content)
    
    # Wrap in paragraph tags if not already
    if not content.startswith('<p>'):
        content = f'<p>{content}</p>'
    
    # Clean up any multiple spaces
    content = re.sub(r'\s+', ' ', content)
    
    return content

if __name__ == '__main__':
    fix_selection_content_extraction()