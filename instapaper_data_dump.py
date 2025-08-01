import hashlib
import json
import os
from time import sleep

import requests
from dotenv import load_dotenv

from helpers.instapaper_api_client import InstapaperAPIClient
from helpers.metadata_manager import (ContentType, MetadataManager,
                                      ProcessingStatus)
from helpers.utils import (calculate_hash, convert_html_to_markdown, log_error,
                           log_info)


def instapaper_data_dump():
    # Load environment variables from .env file
    load_dotenv()

    # Configuration from environment variables
    consumer_key = os.getenv("INSTAPAPER_CONSUMER_KEY")
    consumer_secret = os.getenv("INSTAPAPER_CONSUMER_SECRET")
    username = os.getenv("INSTAPAPER_USERNAME")
    password = os.getenv("INSTAPAPER_PASSWORD")

    # Output paths (ensure these match your Atlas setup)
    data_directory = os.getenv("DATA_DIRECTORY", "output")
    article_output_path = os.path.join(data_directory, "articles")
    meta_save_dir = os.path.join(article_output_path, "metadata")
    md_save_dir = os.path.join(article_output_path, "markdown")
    html_save_dir = os.path.join(article_output_path, "html")
    log_path = os.path.join(article_output_path, "instapaper_dump.log")

    # Create directories if they don't exist
    os.makedirs(meta_save_dir, exist_ok=True)
    os.makedirs(md_save_dir, exist_ok=True)
    os.makedirs(html_save_dir, exist_ok=True)

    if not all([consumer_key, consumer_secret, username, password]):
        log_error(
            log_path,
            "Instapaper API credentials (INSTAPAPER_CONSUMER_KEY, INSTAPAPER_CONSUMER_SECRET, INSTAPAPER_USERNAME, INSTAPAPER_PASSWORD) not found in .env file. Please set them.",
        )
        print(
            "Error: Instapaper API credentials not set in .env. See instapaper_data_dump.py for details."
        )
        return

    client = InstapaperAPIClient(consumer_key, consumer_secret)
    metadata_manager = MetadataManager(
        {"data_directory": data_directory, "article_output_path": article_output_path}
    )

    log_info(log_path, "Attempting to authenticate with Instapaper API...")
    if not client.authenticate(username, password):
        log_error(
            log_path,
            "Instapaper API authentication failed. Check your username, password, consumer key, and consumer secret.",
        )
        print("Error: Instapaper API authentication failed. Check your .env settings.")
        return
    log_info(log_path, "Authentication successful.")

    all_bookmarks = []
    page = 1
    while True:
        log_info(log_path, f"Fetching bookmarks, page {page}...")
        # Instapaper API returns up to 500 bookmarks per call
        # The 'have' parameter is used for synchronization, but for a full dump, we'll just keep fetching.
        # For simplicity, we'll fetch in chunks and assume we get new ones until an empty list is returned.
        # A more robust solution would use the 'have' parameter to avoid re-fetching known bookmarks.
        bookmarks_chunk = client.list_bookmarks(limit=500)  # Fetch max per page
        if not bookmarks_chunk:
            log_info(log_path, "No more bookmarks to fetch.")
            break

        # Filter out bookmarks that are already in all_bookmarks (simple deduplication for this dump)
        new_bookmarks = [
            b
            for b in bookmarks_chunk
            if b.get("bookmark_id") not in [x.get("bookmark_id") for x in all_bookmarks]
        ]
        if not new_bookmarks:
            log_info(log_path, "No new bookmarks on this page. Ending fetch.")
            break

        all_bookmarks.extend(new_bookmarks)
        log_info(
            log_path,
            f"Fetched {len(new_bookmarks)} new bookmarks. Total fetched: {len(all_bookmarks)}.",
        )
        sleep(0.5)  # Be kind to the API
        page += 1

    log_info(log_path, f"Total unique bookmarks fetched: {len(all_bookmarks)}")
    print(f"Total unique bookmarks fetched: {len(all_bookmarks)}")

    processed_count = 0
    for bookmark in all_bookmarks:
        title = bookmark.get("title", "No Title")
        original_url = bookmark.get("url")
        bookmark_id = bookmark.get("bookmark_id")

        if not original_url:
            log_error(log_path, f"Bookmark {bookmark_id} has no URL. Skipping.")
            continue

        uid = hashlib.sha1(original_url.encode("utf-8")).hexdigest()[:16]

        # Check if already processed using MetadataManager
        if metadata_manager.exists(ContentType.INSTAPAPER, uid):
            log_info(
                log_path, f"Article '{title}' ({uid}) already processed. Skipping."
            )
            continue

        metadata = metadata_manager.create_metadata(
            content_type=ContentType.INSTAPAPER,
            source=original_url,
            title=title,
            type_specific={"bookmark_id": bookmark_id},
        )
        metadata.status = ProcessingStatus.STARTED
        metadata_manager.save_metadata(metadata)

        try:
            log_info(log_path, f"Fetching content for '{title}' from {original_url}")

            # Fetch the actual content from the original URL
            response = requests.get(original_url, timeout=30)
            response.raise_for_status()
            html_content = response.text

            html_path = os.path.join(html_save_dir, f"{uid}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            markdown_content = convert_html_to_markdown(html_content, original_url)
            md_path = os.path.join(md_save_dir, f"{uid}.md")
            with open(md_path, "w", encoding="utf-8") as mdf:
                mdf.write(markdown_content)

            metadata.content_path = md_path
            metadata.html_path = html_path
            metadata.source_hash = calculate_hash(md_path)
            metadata.set_success()
            metadata_manager.save_metadata(metadata)

            log_info(log_path, f"Successfully processed and saved '{title}'.")
            processed_count += 1
            sleep(1)  # Be kind to the servers
        except requests.exceptions.RequestException as e:
            error_msg = (
                f"Failed to fetch content for '{title}' from {original_url}: {e}"
            )
            log_error(log_path, error_msg)
            metadata.set_error(error_msg)
            metadata_manager.save_metadata(metadata)
        except Exception as e:
            error_msg = f"Error processing article '{title}': {e}"
            log_error(log_path, error_msg)
            metadata.set_error(error_msg)
            metadata_manager.save_metadata(metadata)

    log_info(
        log_path,
        f"Instapaper data dump finished. Processed {processed_count} new articles.",
    )
    print(f"Instapaper data dump finished. Processed {processed_count} new articles.")


if __name__ == "__main__":
    instapaper_data_dump()
