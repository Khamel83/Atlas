# run.py

import argparse
import glob
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from helpers.article_fetcher import fetch_and_save_articles
from helpers.config import load_config
from helpers.podcast_ingestor import ingest_podcasts
from helpers.safety_monitor import check_pre_run_safety
from helpers.utils import setup_logging
from helpers.youtube_ingestor import ingest_youtube_history
from ingest.link_dispatcher import process_instapaper_csv, process_url_file
from process.recategorize import recategorize_all_content


def main():
    """
    Main function to run the Atlas pipeline.
    """
    # Load environment and configuration
    config = load_config()

    # Safety and compliance check
    if not check_pre_run_safety(config):
        print("❌ Safety check failed. Exiting.")
        return

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the Atlas pipeline")
    parser.add_argument("--articles", action="store_true", help="Run article ingestion")
    parser.add_argument("--podcasts", action="store_true", help="Run podcast ingestion")
    parser.add_argument("--youtube", action="store_true", help="Run YouTube ingestion")
    parser.add_argument(
        "--instapaper-csv",
        type=str,
        help="Path to a clean Instapaper CSV file to ingest",
    )
    parser.add_argument(
        "--recategorize", action="store_true", help="Run recategorization"
    )
    parser.add_argument("--all", action="store_true", help="Run all ingestion types")
    parser.add_argument(
        "--urls", type=str, help="Path to a file containing URLs to ingest"
    )
    args = parser.parse_args()

    # If no arguments are provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return

    # Setup logging
    log_file_path = os.path.join(config.get("data_directory"), "Full_Pipeline.log")
    setup_logging(log_file_path)
    logging.info("-------------------")
    logging.info("Atlas Pipeline Start")
    logging.info("-------------------")

    # Check for legacy retries.json and migrate if needed
    retries_json_path = Path("retries.json")
    if retries_json_path.exists():
        logging.info("Found legacy retries.json file. Migrating to new retry queue...")
        from scripts.migrate_retry_queue import migrate_retry_queue

        migrate_success = migrate_retry_queue(config)
        if migrate_success:
            logging.info("Migration completed successfully.")
        else:
            logging.error("Migration failed. Check the logs for details.")
            # Continue with the pipeline anyway

    # Run the requested ingestion types
    if args.all or args.articles:
        logging.info("Starting article ingestion...")
        fetch_and_save_articles(config)
        logging.info("Article ingestion complete.")

    if args.all or args.podcasts:
        logging.info("Starting podcast ingestion...")
        ingest_podcasts(config)
        logging.info("Podcast ingestion complete.")

    if args.all or args.youtube:
        logging.info("Starting YouTube ingestion...")
        ingest_youtube_history(config)
        logging.info("YouTube ingestion complete.")

    if args.instapaper_csv:
        logging.info(f"Processing Instapaper CSV from {args.instapaper_csv}...")
        results = process_instapaper_csv(args.instapaper_csv, config)
        logging.info(
            f"Instapaper CSV processing complete. Processed {len(results['successful'])} URLs successfully."
        )
        logging.info(f"Skipped {len(results['duplicate'])} duplicate URLs.")
        logging.info(f"Failed to process {len(results['failed'])} URLs.")
        logging.info(f"Unsupported URL types: {len(results['unknown'])}")

    if args.urls:
        logging.info(f"Processing URLs from {args.urls}...")
        results = process_url_file(args.urls, config)
        logging.info(
            f"URL processing complete. Processed {len(results['successful'])} URLs successfully."
        )
        logging.info(f"Skipped {len(results['duplicate'])} duplicate URLs.")
        logging.info(f"Failed to process {len(results['failed'])} URLs.")
        logging.info(f"Unsupported URL types: {len(results['unknown'])}")

    if args.recategorize:
        logging.info("Starting recategorization...")
        recategorize_all_content(config)
        logging.info("Recategorization complete.")

    logging.info("-----------------")
    logging.info("Atlas Pipeline End")
    logging.info("-----------------")


if __name__ == "__main__":
    main()
