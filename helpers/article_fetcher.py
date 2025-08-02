"""
Article Fetcher Module - Simplified Post-Migration

This module provides article fetching functionality by delegating to the
ArticleFetcher strategy orchestrator in article_strategies.py.

All complex fetching logic (paywall bypass, Playwright, archive retrieval, etc.)
has been moved to the strategy pattern for better maintainability and testability.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from helpers.article_strategies import ArticleFetcher
from helpers.config import load_config
from helpers.evaluation_utils import EvaluationFile
from helpers.utils import calculate_hash, generate_markdown_summary, log_error, log_info
from helpers.retry_queue import enqueue
from process.evaluate import classify_content, extract_entities, summarize_text


def fetch_and_save_article(url: str, config: dict) -> bool:
    """
    Fetch and save a single article from a URL using the ArticleFetcher strategy orchestrator.
    
    Args:
        url: The URL to fetch
        config: The application configuration dictionary
    
    Returns:
        bool: True if successful, False otherwise
    """
    output_path = config["article_output_path"]
    html_save_dir = os.path.join(output_path, "html")
    meta_save_dir = os.path.join(output_path, "metadata")
    md_save_dir = os.path.join(output_path, "markdown")
    log_path = os.path.join(output_path, "ingest.log")
    
    # Ensure directories exist
    os.makedirs(html_save_dir, exist_ok=True)
    os.makedirs(meta_save_dir, exist_ok=True)
    os.makedirs(md_save_dir, exist_ok=True)

    # Generate unique file ID
    url_hash = calculate_hash(url)
    html_path = os.path.join(html_save_dir, f"{url_hash}.html")
    meta_path = os.path.join(meta_save_dir, f"{url_hash}.json")
    md_path = os.path.join(md_save_dir, f"{url_hash}.md")

    # Check if already processed
    if os.path.exists(meta_path):
        log_info(log_path, f"Skipping {url} - already exists")
        return True

    try:
        fetch_start_time = datetime.now()
        
        # Use the ArticleFetcher strategy orchestrator for all fetching
        log_info(log_path, f"Starting fetch for {url}")
        fetcher = ArticleFetcher()
        result = fetcher.fetch_with_fallbacks(url, log_path)
        
        if not result.success or not result.content:
            log_error(log_path, f"Failed to fetch content for {url}: {result.error}")
            # Add to retry queue for later processing
            enqueue(config, {
                "type": "article",
                "url": url,
                "file_id": url_hash,
                "error": result.error or "All fetch strategies failed",
                "timestamp": datetime.now().isoformat(),
                "attempts": 1
            })
            return False

        # Save raw HTML
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(result.content)

        # Generate markdown content
        markdown_content = generate_markdown_summary(result.content, url)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # Prepare metadata
        fetch_end_time = datetime.now()
        fetch_duration = (fetch_end_time - fetch_start_time).total_seconds()
        
        metadata = {
            "uid": url_hash,
            "url": url,
            "title": result.title or "No title found",
            "fetch_time": fetch_start_time.isoformat(),
            "fetch_duration": fetch_duration,
            "fetch_method": result.method,
            "success": True,
            "content_length": len(result.content),
            "markdown_length": len(markdown_content),
            "is_truncated": result.is_truncated,
            "fetch_details": {
                "successful_method": result.method,
                "attempts": result.metadata.get("attempts", []) if result.metadata else [],
                "total_attempts": len(result.metadata.get("attempts", [])) if result.metadata else 1,
                "is_truncated": result.is_truncated,
                "fetch_time": fetch_duration,
            }
        }

        # Run AI evaluations if enabled
        try:
            if config.get("enable_ai_evaluation", False):
                log_info(log_path, f"Running AI evaluations for {url}")
                
                # Content classification
                classification = classify_content(markdown_content)
                metadata["classification"] = classification

                # Entity extraction
                entities = extract_entities(markdown_content)
                metadata["entities"] = entities

                # Content summarization
                summary = summarize_text(markdown_content)
                metadata["summary"] = summary
                
                log_info(log_path, f"AI evaluations completed for {url}")
                
        except Exception as eval_error:
            log_error(log_path, f"AI evaluation failed for {url}: {eval_error}")
            metadata["evaluation_error"] = str(eval_error)

        # Save metadata
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Create evaluation file entry
        try:
            eval_file = EvaluationFile(config)
            eval_file.add_entry(url_hash, {
                "url": url,
                "title": metadata["title"],
                "fetch_method": result.method,
                "content_length": len(result.content),
                "success": True,
                "timestamp": fetch_start_time.isoformat()
            })
        except Exception as eval_error:
            log_error(log_path, f"Failed to update evaluation file for {url}: {eval_error}")

        log_info(log_path, f"Successfully processed {url} using {result.method}")
        return True

    except Exception as e:
        log_error(log_path, f"Unexpected error processing {url}: {e}")
        
        # Add to retry queue
        enqueue(config, {
            "type": "article",
            "url": url,
            "file_id": url_hash,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "attempts": 1
        })
        
        return False


def fetch_and_save_articles(config: dict) -> dict:
    """
    Fetch and save articles from the configured input sources.
    
    Args:
        config: Application configuration dictionary
        
    Returns:
        dict: Summary of processing results
    """
    urls_file = config.get("articles_input_file", "inputs/articles.txt")
    
    if not os.path.exists(urls_file):
        log_error("", f"Articles input file not found: {urls_file}")
        return {"success": 0, "failed": 0, "total": 0}
    
    # Read URLs from file
    urls = []
    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    if not urls:
        log_info("", "No URLs found in articles input file")
        return {"success": 0, "failed": 0, "total": 0}
    
    log_info("", f"Processing {len(urls)} articles from {urls_file}")
    
    success_count = 0
    failed_count = 0
    
    for url in urls:
        try:
            if fetch_and_save_article(url, config):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            log_error("", f"Error processing {url}: {e}")
            failed_count += 1
    
    results = {
        "success": success_count,
        "failed": failed_count,
        "total": len(urls)
    }
    
    log_info("", f"Article processing complete: {success_count} success, {failed_count} failed")
    return results


# Backward compatibility functions (deprecated)
def fetch_and_save_articles_legacy(urls, output_dir):
    """
    Legacy function for backward compatibility.
    
    DEPRECATED: Use fetch_and_save_articles() with proper config instead.
    """
    config = load_config()
    config["article_output_path"] = output_dir
    
    # Convert to the new format expected by fetch_and_save_articles
    urls_file = "temp_urls.txt"
    with open(urls_file, "w") as f:
        for url in urls:
            f.write(f"{url}\n")
    
    config["articles_input_file"] = urls_file
    
    try:
        result = fetch_and_save_articles(config)
        return result["success"] > 0
    finally:
        # Clean up temp file
        if os.path.exists(urls_file):
            os.remove(urls_file)