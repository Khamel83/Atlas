import re
import os
import requests
import json
from datetime import datetime
import hashlib
import logging
from markdownify import markdownify as md

def convert_html_to_markdown(html_content: str, base_url: str = None) -> str:
    """
    Converts HTML content to Markdown, optionally preserving links.
    Args:
        html_content (str): The HTML string to convert.
        base_url (str): The base URL to resolve relative links (optional).
    Returns:
        str: The converted Markdown string.
    """
    # markdownify options can be tuned here if needed
    # e.g., heading_style="ATX"
    return md(html_content, base_url=base_url)

def ensure_directory(directory_path: str):
    """
    Ensures a directory exists, creating it if necessary.
    
    Args:
        directory_path (str): Path to the directory to create
    """
    os.makedirs(directory_path, exist_ok=True)

def setup_logging(log_path: str):
    """
    Configures the root logger to output to both a file and the console.
    """
    log_dir = os.path.dirname(log_path)
    ensure_directory(log_dir)
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create file handler
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

def sanitize_filename(name):
    # Replace spaces and special chars with underscores
    name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    name = re.sub(r"[-\s]+", "_", name)
    return name

def extract_video_id(url):
    """
    Extracts the YouTube video ID from a URL.
    Supports standard and shortened URL formats.
    """
    regex_patterns = [
        r"youtu\.be/([^\?&]+)",
        r"youtube\.com/watch\?v=([^\?&]+)",
        r"youtube\.com/embed/([^\?&]+)",
        r"youtube\.com/v/([^\?&]+)",
        r"youtube\.com/shorts/([^\?&]+)"
    ]

    for pattern in regex_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def generate_markdown_summary(title, source, date, tags=None, notes=None, content=None):
    """
    Generate a Markdown summary report with YAML frontmatter.
    Args:
        title (str): Title of the item
        source (str): Source URL or identifier
        date (str): Date string
        tags (list): List of tags (optional)
        notes (list): List of bullet notes (optional)
        content (str): Main content (transcript, article body, etc.)
    Returns:
        str: Markdown-formatted summary
    """
    tags = tags or []
    notes = notes or []

    frontmatter = [
        f"title: {title}",
        f"description: {description}",
	f"tags: [{', '.join([repr(t) for t in tags])}]"
    ]

    for note in notes:
        frontmatter.append(f"- {note}")
    frontmatter.append('---\n')

    md = '\n'.join(frontmatter)
    if content:
        md += content.strip() + "\n"
    return md

def log_message(log_path, level, message):
    """Generic logger for INFO and ERROR messages."""
    if not log_path:
        return  # No-op if log_path is empty or None
    # Ensure the directory for the log file exists
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_line = f"{datetime.now().isoformat()} {level}: {message}\n"
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(log_line)
    # Also print to console
    print(log_line.strip())

def log_info(log_path, message):
    if not log_path:
        return
    log_message(log_path, "INFO", message)

def log_error(log_path, message):
    if not log_path:
        return
    log_message(log_path, "ERROR", message)

def calculate_hash(file_path):
    """Calculates the SHA256 hash of a file's content."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()
