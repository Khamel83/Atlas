#!/usr/bin/env python3
"""
Comprehensive Content Quality Analyzer for Instapaper Integration

Analyzes all converted files to determine:
1. Which files contain actual article content vs stubs/placeholders
2. Content quality metrics (word count, meaningful content ratio)
3. Categorization: Real content, Minimal, Stub, Private placeholder, Failed
4. Detailed breakdown with file IDs, URLs, and actionable recommendations

This is critical for understanding what we ACTUALLY captured vs what needs
to be processed through Atlas's main content fetching pipeline.
"""

import os
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import statistics

class InstapaperContentAnalyzer:
    
    def __init__(self, output_base="output/articles"):
        self.output_base = output_base
        self.html_dir = os.path.join(output_base, "html")
        self.metadata_dir = os.path.join(output_base, "metadata") 
        self.markdown_dir = os.path.join(output_base, "markdown")
        
        # Our known placeholder/stub patterns
        self.stub_patterns = [
            "Content would need to be fetched separately",
            "This bookmark was imported from Instapaper",
            "cannot be directly accessed via URL",
            "private content from Instapaper",
            "would need to be accessed through Instapaper",
            "This is private content from Instapaper"
        ]
        
        # HTML structure patterns to exclude from content analysis
        self.html_structure_patterns = [
            r'<title>.*?</title>',
            r'<h1>.*?</h1>',
            r'<div class="instapaper-info">.*?</div>',
            r'<p><strong>Source:</strong>.*?</p>',
            r'<p><strong>Folder:</strong>.*?</p>',
            r'<p><strong>Added:</strong>.*?</p>',
            r'<p><strong>Tags:</strong>.*?</p>'
        ]
    
    def analyze_all_files(self):
        """Analyze all converted Instapaper files for content quality"""
        
        print("🔍 INSTAPAPER CONTENT QUALITY ANALYSIS")
        print("=" * 60)
        print(f"📁 Analyzing files in: {self.output_base}")
        print()
        
        # Get all HTML files (our primary content files)
        if not os.path.exists(self.html_dir):
            print(f"❌ HTML directory not found: {self.html_dir}")
            return
        
        html_files = [f for f in os.listdir(self.html_dir) if f.endswith('.html')]
        total_files = len(html_files)
        
        print(f"📊 Found {total_files:,} files to analyze")
        print("🔄 Processing files...")
        print()
        
        # Analysis results
        results = {
            'total_files': total_files,
            'categories': {
                'real_content': [],      # Substantial article content
                'minimal_content': [],   # Some content but very short
                'stub_placeholder': [],  # Our template stubs
                'private_placeholder': [], # Private content placeholders
                'failed_empty': [],      # Empty or broken files
                'unknown': []            # Unclear category
            },
            'statistics': {},
            'quality_metrics': [],
            'actionable_urls': []  # URLs that need real content fetching
        }
        
        # Process each file
        for i, filename in enumerate(html_files):
            if i > 0 and i % 100 == 0:
                print(f"  Progress: {i}/{total_files} files analyzed...")
            
            file_id = filename.replace('.html', '')
            analysis = self.analyze_single_file(file_id)
            
            if analysis:
                results['quality_metrics'].append(analysis)
                category = analysis['category']
                results['categories'][category].append(analysis)
                
                # Track URLs that need content fetching
                if category in ['stub_placeholder', 'minimal_content'] and analysis['has_fetchable_url']:
                    results['actionable_urls'].append({
                        'file_id': file_id,
                        'url': analysis['url'],
                        'title': analysis['title'],
                        'category': category,
                        'reason': analysis['category_reason']
                    })
        
        # Calculate statistics
        results['statistics'] = self.calculate_statistics(results['quality_metrics'])
        
        # Generate comprehensive report
        self.generate_detailed_report(results)
        
        return results
    
    def analyze_single_file(self, file_id):
        """Analyze a single converted file for content quality"""
        
        html_path = os.path.join(self.html_dir, f"{file_id}.html")
        metadata_path = os.path.join(self.metadata_dir, f"{file_id}.json")
        
        if not os.path.exists(html_path) or not os.path.exists(metadata_path):
            return None
        
        try:
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load HTML content
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract key information
            title = metadata.get('title', 'Untitled')
            url = metadata.get('source', '')
            type_specific = metadata.get('type_specific', {})
            is_private = type_specific.get('is_private_content', False)
            
            # Analyze content quality
            content_analysis = self.analyze_content_quality(html_content)
            
            # Determine category and reason
            category, reason = self.categorize_content(
                content_analysis, 
                is_private, 
                url, 
                html_content
            )
            
            return {
                'file_id': file_id,
                'title': title,
                'url': url,
                'is_private': is_private,
                'category': category,
                'category_reason': reason,
                'has_fetchable_url': url.startswith('http'),
                'content_analysis': content_analysis,
                'file_size_bytes': os.path.getsize(html_path)
            }
            
        except Exception as e:
            return {
                'file_id': file_id,
                'title': 'Error',
                'url': '',
                'is_private': False,
                'category': 'failed_empty',
                'category_reason': f'Analysis error: {str(e)}',
                'has_fetchable_url': False,
                'content_analysis': {'word_count': 0, 'meaningful_sentences': 0},
                'file_size_bytes': 0
            }
    
    def analyze_content_quality(self, html_content):
        """Extract and analyze the actual article content quality"""
        
        # Remove HTML tags and structure
        content_text = self.extract_main_content(html_content)
        
        # Basic metrics
        word_count = len(content_text.split())
        char_count = len(content_text)
        
        # Sentence analysis
        sentences = [s.strip() for s in re.split(r'[.!?]+', content_text) if s.strip()]
        sentence_count = len(sentences)
        
        # Meaningful content detection
        meaningful_sentences = self.count_meaningful_sentences(sentences)
        
        # Placeholder detection
        placeholder_ratio = self.calculate_placeholder_ratio(content_text)
        
        # Content diversity (repeated phrases indicate templates)
        diversity_score = self.calculate_content_diversity(content_text)
        
        return {
            'word_count': word_count,
            'char_count': char_count,
            'sentence_count': sentence_count,
            'meaningful_sentences': meaningful_sentences,
            'placeholder_ratio': placeholder_ratio,
            'diversity_score': diversity_score,
            'avg_sentence_length': word_count / max(sentence_count, 1)
        }
    
    def extract_main_content(self, html_content):
        """Extract just the main article content, excluding metadata/structure"""
        
        # Remove HTML structure patterns
        text = html_content
        for pattern in self.html_structure_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract content from both <div class="content"> and <div class="selection"> sections
        content_text = ""
        
        # Get main content
        content_match = re.search(r'<div class="content">(.*?)</div>', text, re.DOTALL | re.IGNORECASE)
        if content_match:
            content_text += content_match.group(1) + " "
        
        # Get selection content (this is where the CSV Selection data appears!)
        selection_match = re.search(r'<div class="selection">.*?<p>(.*?)</p>.*?</div>', text, re.DOTALL | re.IGNORECASE)
        if selection_match:
            content_text += selection_match.group(1) + " "
        
        # If we found specific content sections, use those; otherwise use all text
        if content_text.strip():
            text = content_text
        else:
            # Fallback to all remaining text after removing structure
            pass
        
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def count_meaningful_sentences(self, sentences):
        """Count sentences that appear to contain meaningful content"""
        
        meaningful = 0
        
        for sentence in sentences:
            # Skip very short sentences
            if len(sentence.split()) < 4:
                continue
                
            # Skip sentences that are mostly our placeholder text
            is_placeholder = False
            for pattern in self.stub_patterns:
                if pattern.lower() in sentence.lower():
                    is_placeholder = True
                    break
            
            if not is_placeholder:
                meaningful += 1
        
        return meaningful
    
    def calculate_placeholder_ratio(self, content_text):
        """Calculate what percentage of content is our placeholder text"""
        
        if not content_text:
            return 1.0
        
        total_chars = len(content_text)
        placeholder_chars = 0
        
        for pattern in self.stub_patterns:
            # Find all occurrences of this pattern
            for match in re.finditer(re.escape(pattern), content_text, re.IGNORECASE):
                placeholder_chars += len(match.group())
        
        return placeholder_chars / total_chars
    
    def calculate_content_diversity(self, content_text):
        """Calculate content diversity (higher = more unique content)"""
        
        if not content_text:
            return 0.0
        
        words = content_text.lower().split()
        if len(words) < 5:
            return 0.0
        
        unique_words = len(set(words))
        return unique_words / len(words)  # Ratio of unique to total words
    
    def categorize_content(self, content_analysis, is_private, url, html_content):
        """Categorize content and provide reasoning"""
        
        word_count = content_analysis['word_count']
        meaningful_sentences = content_analysis['meaningful_sentences']
        placeholder_ratio = content_analysis['placeholder_ratio']
        
        # Private content that we can't fetch
        if is_private:
            if meaningful_sentences > 3 and word_count > 100:
                return 'real_content', f'Private content with substantial text ({word_count} words)'
            else:
                return 'private_placeholder', f'Private content placeholder ({word_count} words)'
        
        # High placeholder ratio = our stub templates
        if placeholder_ratio > 0.5:
            return 'stub_placeholder', f'High placeholder ratio ({placeholder_ratio:.1%})'
        
        # Empty or very minimal content
        if word_count < 20:
            return 'failed_empty', f'Very minimal content ({word_count} words)'
        
        # Real article content indicators
        if meaningful_sentences >= 5 and word_count >= 200:
            return 'real_content', f'Substantial article content ({word_count} words, {meaningful_sentences} sentences)'
        
        # Minimal but some real content
        if meaningful_sentences >= 2 and word_count >= 50:
            return 'minimal_content', f'Some content but brief ({word_count} words, {meaningful_sentences} sentences)'
        
        # Fallback category
        return 'unknown', f'Unclear content quality ({word_count} words, {meaningful_sentences} sentences)'
    
    def calculate_statistics(self, quality_metrics):
        """Calculate overall statistics from all file analyses"""
        
        if not quality_metrics:
            return {}
        
        word_counts = [m['content_analysis']['word_count'] for m in quality_metrics]
        sentence_counts = [m['content_analysis']['meaningful_sentences'] for m in quality_metrics]
        file_sizes = [m['file_size_bytes'] for m in quality_metrics]
        
        return {
            'word_count_stats': {
                'mean': statistics.mean(word_counts),
                'median': statistics.median(word_counts),
                'min': min(word_counts),
                'max': max(word_counts)
            },
            'sentence_stats': {
                'mean': statistics.mean(sentence_counts),
                'median': statistics.median(sentence_counts),
                'min': min(sentence_counts),
                'max': max(sentence_counts)
            },
            'file_size_stats': {
                'mean': statistics.mean(file_sizes),
                'median': statistics.median(file_sizes),
                'min': min(file_sizes),
                'max': max(file_sizes)
            }
        }
    
    def generate_detailed_report(self, results):
        """Generate comprehensive analysis report"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_file = f"instapaper_content_analysis_report_{timestamp}.json"
        summary_file = f"instapaper_content_analysis_summary_{timestamp}.txt"
        actionable_file = f"instapaper_urls_for_atlas_queue_{timestamp}.txt"
        
        # Save detailed JSON report
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Generate human-readable summary
        self.generate_summary_report(results, summary_file, actionable_file)
        
        # Generate actionable URL list for Atlas processing
        self.generate_actionable_urls(results, actionable_file)
        
        print(f"📋 Analysis complete! Reports saved:")
        print(f"  📊 Detailed report: {report_file}")
        print(f"  📄 Summary report: {summary_file}")  
        print(f"  🎯 URLs for Atlas queue: {actionable_file}")
    
    def generate_summary_report(self, results, filename, actionable_filename):
        """Generate human-readable summary report"""
        
        total = results['total_files']
        categories = results['categories']
        stats = results['statistics']
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("INSTAPAPER CONTENT QUALITY ANALYSIS SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Files Analyzed: {total:,}\n\n")
            
            # Category breakdown
            f.write("CONTENT CATEGORY BREAKDOWN:\n")
            f.write("-" * 40 + "\n")
            
            for category, items in categories.items():
                count = len(items)
                percentage = (count / total * 100) if total > 0 else 0
                
                category_name = category.replace('_', ' ').title()
                f.write(f"  {category_name:20} | {count:5,} files ({percentage:5.1f}%)\n")
                
                # Show sample reasons
                if items:
                    reasons = [item.get('category_reason', 'No reason') for item in items[:3]]
                    for reason in reasons:
                        f.write(f"    Sample: {reason}\n")
                    f.write("\n")
            
            # Statistics
            f.write("\nCONTENT QUALITY STATISTICS:\n")
            f.write("-" * 40 + "\n")
            
            if 'word_count_stats' in stats:
                wc = stats['word_count_stats']
                f.write(f"Word Count - Mean: {wc['mean']:.1f}, Median: {wc['median']:.1f}, Range: {wc['min']}-{wc['max']}\n")
            
            if 'sentence_stats' in stats:
                sc = stats['sentence_stats']
                f.write(f"Meaningful Sentences - Mean: {sc['mean']:.1f}, Median: {sc['median']:.1f}, Range: {sc['min']}-{sc['max']}\n")
            
            # Key findings
            real_content = len(categories.get('real_content', []))
            actionable = len(results.get('actionable_urls', []))
            
            f.write(f"\nKEY FINDINGS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"✅ Files with substantial content: {real_content:,} ({real_content/total*100:.1f}%)\n")
            f.write(f"🔄 Files needing content fetching: {actionable:,} ({actionable/total*100:.1f}%)\n")
            f.write(f"📊 Success rate (real content): {real_content/total*100:.1f}%\n")
            
            # Recommendations
            f.write(f"\nRECOMMENDations:\n")
            f.write("-" * 40 + "\n")
            
            if actionable > 0:
                f.write(f"1. Process {actionable:,} URLs through Atlas content fetching pipeline\n")
                f.write(f"2. These represent fetchable web content with stub placeholders\n")
                f.write(f"3. See '{actionable_filename}' for complete URL list\n")
            
            if real_content > 0:
                f.write(f"4. {real_content:,} files already contain substantial content\n")
                f.write(f"5. These can be used immediately in Atlas cognitive features\n")
    
    def generate_actionable_urls(self, results, filename):
        """Generate list of URLs that need content fetching for Atlas queue"""
        
        actionable_urls = results.get('actionable_urls', [])
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# URLs for Atlas Content Fetching Queue\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total URLs: {len(actionable_urls):,}\n")
            f.write("#\n")
            f.write("# These are Instapaper bookmarks that currently only have stub/placeholder content\n")
            f.write("# and need to be processed through Atlas's main content fetching pipeline\n")
            f.write("#\n")
            f.write("# Format: URL (one per line, ready for Atlas processing)\n")
            f.write("\n")
            
            for item in actionable_urls:
                url = item['url']
                title = item['title'][:60]  # Truncate long titles
                f.write(f"{url}\n")
            
            f.write(f"\n# End of list - {len(actionable_urls):,} URLs total\n")
        
        print(f"\n🎯 ACTIONABLE RESULTS:")
        print(f"  📊 {len(actionable_urls):,} URLs identified for Atlas content fetching")
        print(f"  📁 Saved to: {filename}")
        print(f"  🔄 These can be added to Atlas processing queue")

def main():
    """Run the comprehensive content quality analysis"""
    
    print("🚀 Starting Instapaper Content Quality Analysis...")
    print("This will analyze all converted files to determine actual content quality")
    print()
    
    analyzer = InstapaperContentAnalyzer()
    results = analyzer.analyze_all_files()
    
    if results:
        total = results['total_files']
        real_content = len(results['categories'].get('real_content', []))
        actionable = len(results.get('actionable_urls', []))
        
        print(f"\n🎉 ANALYSIS COMPLETE!")
        print(f"📊 {total:,} files analyzed")
        print(f"✅ {real_content:,} files with real content ({real_content/total*100:.1f}%)")
        print(f"🔄 {actionable:,} URLs need content fetching ({actionable/total*100:.1f}%)")
        print()
        print("📋 Detailed reports generated - check the files above!")

if __name__ == '__main__':
    main()