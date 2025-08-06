#!/usr/bin/env python3
"""
Clean up redundant Selection content display in markdown files
"""

import os
import re
from datetime import datetime

def cleanup_selection_format():
    """Remove redundant Selection content display"""
    
    print("🧹 CLEANING UP SELECTION CONTENT FORMAT")
    print("=" * 50)
    
    markdown_dir = "output/articles/markdown"
    
    if not os.path.exists(markdown_dir):
        print(f"❌ Markdown directory not found: {markdown_dir}")
        return
    
    # Find files with Selection content
    md_files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')]
    
    print(f"🔍 Checking {len(md_files):,} markdown files for Selection content...")
    
    files_with_selection = 0
    files_cleaned = 0
    
    for md_file in md_files:
        md_path = os.path.join(markdown_dir, md_file)
        
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if this file has Selection content
            if 'Selected Content' in content and 'Original Selection' in content:
                files_with_selection += 1
                
                # Clean up the format
                cleaned_content = clean_selection_content(content)
                
                # Write back the cleaned version
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                files_cleaned += 1
                
                if files_cleaned % 100 == 0:
                    print(f"  ✅ Cleaned {files_cleaned} files...")
        
        except Exception as e:
            print(f"  ❌ Error processing {md_file}: {e}")
            continue
    
    print(f"\n🎯 CLEANUP COMPLETE!")
    print(f"  📊 Files with Selection content: {files_with_selection:,}")
    print(f"  ✅ Files cleaned: {files_cleaned:,}")
    
    print(f"\n✨ Selection content is now clean and non-redundant!")

def clean_selection_content(content):
    """Clean up redundant Selection content in a markdown file"""
    
    # Pattern to match the redundant structure
    pattern = r'## Selected Content\n\n(.*?)\n\n---\n\n\*This content was extracted.*?\*\n\n### Original Selection\n\n> (.*?)(?=\n\n|\Z)'
    
    # Replace with clean version
    def replace_selection(match):
        selected_content = match.group(1)
        
        # Clean up the HTML content to make it more readable
        cleaned = clean_html_content(selected_content)
        
        return f"""## Selected Content

{cleaned}

---

*This content was extracted from your Instapaper Selection field.*"""
    
    # Apply the replacement
    cleaned = re.sub(pattern, replace_selection, content, flags=re.DOTALL)
    
    return cleaned

def clean_html_content(html_content):
    """Clean up HTML content for better readability"""
    
    # Convert HTML paragraph tags to markdown
    content = html_content
    
    # Replace <p> tags with proper paragraphs
    content = re.sub(r'<p>', '\n', content)
    content = re.sub(r'</p>', '\n', content)
    
    # Replace <br> tags with line breaks
    content = re.sub(r'<br>', '  \n', content)
    
    # Clean up multiple newlines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in content.split('\n')]
    content = '\n'.join(lines)
    
    # Remove empty lines at start/end
    content = content.strip()
    
    return content

if __name__ == '__main__':
    cleanup_selection_format()