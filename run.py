# run.py - Atlas-Podemos Unified Entry Point with Database Integration

import argparse
import glob
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Atlas imports
from helpers.article_fetcher import fetch_and_save_articles
from helpers.safety_monitor import check_pre_run_safety
from helpers.utils import setup_logging
from helpers.youtube_ingestor import ingest_youtube_history
from ingest.link_dispatcher import process_instapaper_csv, process_url_file
from process.recategorize import recategorize_all_content

# Database integration
from helpers.atlas_database_helper import get_atlas_database_manager

# Unified configuration and processing
from helpers.config_unified import load_unified_config, is_podcast_processing_enabled, get_podcast_feeds
from helpers.podcast_processor_unified import unified_processor, initialize_podcast_database

# Unified RSS ingestor
from helpers.podcast_rss_unified import get_unified_rss_ingestor

# Ad detection and removal system
from helpers.podcast_ad_processor import get_podcast_ad_processor

# Web interface
import uvicorn
from web.app import app as web_app

def main():
    """
    Main function to run the unified Atlas-Podemos pipeline with database integration.
    """
    # Load unified configuration
    config = load_unified_config()
    
    # Initialize unified database system
    try:
        atlas_db = get_atlas_database_manager()
        if atlas_db.database_enabled:
            print("✅ Atlas unified database initialized successfully")
            
            # Display database statistics
            stats = atlas_db.get_content_statistics()
            print(f"📊 Database contains {stats.get('total_content', 0)} items")
            if stats.get('content_by_type'):
                for content_type, count in stats['content_by_type'].items():
                    print(f"   • {content_type}: {count} items")
        else:
            print("⚠️ Running in file-based mode (database unavailable)")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
        print("   Continuing in file-based mode...")
    
    # Safety and compliance check (Atlas)
    if not check_pre_run_safety(config.atlas_config):
        print("❌ Atlas safety check failed. Exiting.")
        return

    # Initialize podcast database if needed
    if is_podcast_processing_enabled(config):
        if not initialize_podcast_database():
            print("⚠️ Failed to initialize podcast database. Podcast processing disabled.")
            config.podcast_processing_enabled = False

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the unified Atlas-Podemos pipeline")
    
    # Atlas arguments
    parser.add_argument("--articles", action="store_true", help="Run article ingestion")
    parser.add_argument("--youtube", action="store_true", help="Run YouTube ingestion")
    parser.add_argument("--instapaper-csv", type=str, help="Path to a clean Instapaper CSV file to ingest")
    parser.add_argument("--recategorize", action="store_true", help="Run recategorization")
    parser.add_argument("--urls", type=str, help="Path to a file containing URLs to ingest")
    
    # Podcast processing arguments (Podemos enhanced)
    parser.add_argument("--podcasts", action="store_true", help="Run advanced podcast processing")
    parser.add_argument("--podcasts-basic", action="store_true", help="Run basic Atlas podcast processing")
    parser.add_argument("--init-podcast-db", action="store_true", help="Initialize podcast database")
    parser.add_argument("--poll-feeds", action="store_true", help="Poll RSS feeds for new episodes")
    parser.add_argument("--add-feed", type=str, help="Add a new podcast feed URL")
    parser.add_argument("--import-opml", type=str, help="Import feeds from OPML file")
    parser.add_argument("--process-episode", type=int, help="Process specific episode by ID")
    parser.add_argument("--episode-status", action="store_true", help="Show episode processing status")
    
    # Unified RSS ingestor arguments  
    parser.add_argument("--rss-ingest", type=str, help="Ingest RSS feed using unified ingestor")
    parser.add_argument("--rss-stats", action="store_true", help="Show unified RSS ingestor statistics")
    parser.add_argument("--rss-poll-feeds", action="store_true", help="Poll feeds using unified RSS ingestor")
    
    # Ad detection and removal arguments
    parser.add_argument("--process-audio", type=str, help="Process audio URL with ad detection and removal")
    parser.add_argument("--ad-stats", action="store_true", help="Show ad processing statistics")
    parser.add_argument("--batch-process-ads", type=str, help="Batch process episodes from JSON file")
    
    # Cognitive analysis arguments  
    parser.add_argument("--cognitive-analysis", action="store_true", help="Run cognitive analysis on processed content")
    parser.add_argument("--analyze-episode", type=int, help="Run cognitive analysis on specific episode")
    
    # Database integration arguments
    parser.add_argument("--init-unified-db", action="store_true", help="Initialize unified database")
    parser.add_argument("--migrate-atlas", action="store_true", help="Migrate Atlas content to unified database")
    parser.add_argument("--validate-db", action="store_true", help="Validate database integrity")
    parser.add_argument("--db-stats", action="store_true", help="Show database statistics")
    parser.add_argument("--db-path", type=str, help="Path to unified database file")
    
    # System arguments
    parser.add_argument("--all", action="store_true", help="Run all ingestion types")
    parser.add_argument("--serve", action="store_true", help="Start web server with integrated dashboard")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default: 8000)")
    
    args = parser.parse_args()

    # Set up logging
    from helpers.config import load_config
    log_path = "logs/atlas_unified.log"
    basic_config = load_config()  # For logging setup
    setup_logging(log_path, basic_config)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting Atlas-Podemos unified system")
    logger.info(f"Integration mode: {config.integration_mode}")
    logger.info(f"Podcast processing enabled: {config.podcast_processing_enabled}")
    logger.info(f"Cognitive analysis enabled: {config.cognitive_analysis_enabled}")

    # Handle database integration commands
    if args.init_unified_db:
        from database_integration.init_unified_db import create_unified_database_schema
        db_path = args.db_path or "atlas_unified.db"
        if create_unified_database_schema(db_path):
            print(f"✅ Unified database initialized: {db_path}")
        else:
            print(f"❌ Failed to initialize unified database: {db_path}")
        return
    
    if args.migrate_atlas:
        from database_integration.migrate_atlas_content import AtlasContentMigrator
        db_path = args.db_path or "atlas_unified.db"
        migrator = AtlasContentMigrator(db_path, ".")
        if migrator.migrate_all_content():
            print(f"✅ Atlas content migrated to: {db_path}")
        else:
            print(f"❌ Atlas content migration failed")
        return
    
    if args.validate_db:
        from database_integration.validate_migration import MigrationValidator
        db_path = args.db_path or "atlas_unified.db"
        validator = MigrationValidator(db_path)
        if validator.run_full_validation():
            print(f"✅ Database validation passed: {db_path}")
        else:
            print(f"⚠️ Database validation found issues: {db_path}")
        return
    
    if args.db_stats:
        try:
            atlas_db = get_atlas_database_manager(args.db_path)
            stats = atlas_db.get_content_statistics()
            print("\n📊 UNIFIED DATABASE STATISTICS")
            print("=" * 50)
            print(f"Total content items: {stats.get('total_content', 0)}")
            print(f"Content by type: {stats.get('content_by_type', {})}")
            print(f"Content by status: {stats.get('content_by_status', {})}")
            print(f"Items with errors: {stats.get('content_with_errors', 0)}")
            if stats.get('total_content', 0) > 0:
                error_rate = (stats.get('content_with_errors', 0) / stats['total_content']) * 100
                print(f"Error rate: {error_rate:.1f}%")
            atlas_db.close()
        except Exception as e:
            print(f"❌ Failed to get database statistics: {e}")
        return

    # Handle podcast database initialization
    if args.init_podcast_db:
        if initialize_podcast_database():
            print("✅ Podcast database initialized successfully")
        else:
            print("❌ Failed to initialize podcast database")
        return

    # Handle feed management
    if args.add_feed:
        result = unified_processor.poll_podcast_feeds([args.add_feed])
        if result["success"]:
            print(f"✅ Successfully added feed: {args.add_feed}")
        else:
            print(f"❌ Failed to add feed: {args.add_feed}")
        return

    if args.import_opml:
        result = unified_processor.import_opml_feeds(args.import_opml)
        if result["success"]:
            print(f"✅ Successfully imported OPML from: {args.import_opml}")
        else:
            print(f"❌ Failed to import OPML: {result.get('error', 'Unknown error')}")
        return

    # Handle episode processing
    if args.process_episode:
        if not is_podcast_processing_enabled(config):
            print("❌ Podcast processing is not enabled")
            return
        
        result = unified_processor.process_episode_advanced(args.process_episode)
        if result["success"]:
            print(f"✅ Successfully processed episode {args.process_episode}")
        else:
            print(f"❌ Failed to process episode {args.process_episode}: {result.get('error', 'Unknown error')}")
        return

    # Handle episode status
    if args.episode_status:
        status = unified_processor.get_episode_status()
        print(f"📊 Episode Status: {status['total']} total episodes")
        for episode in status["episodes"][:10]:  # Show first 10
            print(f"  {episode['id']}: {episode['title']} [{episode['status']}]")
        return

    # Handle feed polling
    if args.poll_feeds:
        if not is_podcast_processing_enabled(config):
            print("❌ Podcast processing is not enabled")
            return
        
        feeds = get_podcast_feeds(config)
        if not feeds:
            print("⚠️ No podcast feeds configured")
            return
        
        print(f"📡 Polling {len(feeds)} podcast feeds...")
        result = unified_processor.poll_podcast_feeds(feeds)
        print(f"✅ Successfully polled {len(result['success'])} feeds")
        if result["failed"]:
            print(f"❌ Failed to poll {len(result['failed'])} feeds")
        return

    # Handle web server
    if args.serve:
        print(f"🌐 Starting unified Atlas-Podemos web server on port {args.port}")
        print(f"   Dashboard: http://localhost:{args.port}/ask/html")
        print(f"   Podcast Management: http://localhost:{args.port}/podcasts/")
        uvicorn.run(web_app, host="0.0.0.0", port=args.port)
        return

    # Handle traditional Atlas processing
    if args.articles:
        print("📰 Processing articles...")
        fetch_and_save_articles()

    if args.youtube:
        print("🎥 Processing YouTube content...")
        ingest_youtube_history()

    if args.podcasts_basic:
        print("🎧 Processing podcasts (basic Atlas mode)...")
        # Use original Atlas podcast processing
        from helpers.podcast_ingestor import ingest_podcasts
        ingest_podcasts()

    if args.podcasts:
        if not is_podcast_processing_enabled(config):
            print("❌ Advanced podcast processing is not enabled")
            print("   Use --podcasts-basic for basic Atlas processing")
            return
        
        print("🎧 Processing podcasts (advanced Podemos mode)...")
        feeds = get_podcast_feeds(config)
        if feeds:
            result = unified_processor.poll_podcast_feeds(feeds)
            print(f"✅ Successfully processed {len(result['success'])} feeds")
        else:
            print("⚠️ No podcast feeds configured. Use --add-feed or --import-opml to set up feeds.")

    # Unified RSS ingestor commands
    if args.rss_ingest:
        print(f"📡 Ingesting RSS feed with unified ingestor: {args.rss_ingest}")
        rss_ingestor = get_unified_rss_ingestor(config)
        success = rss_ingestor.ingest_feed_url(args.rss_ingest)
        if success:
            print("✅ RSS feed ingestion completed successfully")
        else:
            print("❌ RSS feed ingestion failed")
        rss_ingestor.close()
    
    if args.rss_stats:
        print("📊 Unified RSS ingestor statistics:")
        rss_ingestor = get_unified_rss_ingestor(config)
        stats = rss_ingestor.get_processing_stats()
        if 'error' in stats:
            print(f"   ❌ Error retrieving stats: {stats['error']}")
        else:
            print(f"   📈 Total episodes: {stats.get('total_episodes', 0)}")
            print(f"   📥 Ingested: {stats.get('ingested', 0)}")
            print(f"   ⚙️  Processing: {stats.get('processing', 0)}")
            print(f"   ✅ Completed: {stats.get('completed', 0)}")
            print(f"   🗄️  Database enabled: {stats.get('database_enabled', False)}")
        rss_ingestor.close()
    
    if args.rss_poll_feeds:
        print("📡 Polling RSS feeds with unified ingestor...")
        feeds = []
        
        # Try to get feeds from config
        if is_podcast_processing_enabled(config):
            feeds = get_podcast_feeds(config)
        
        # Fallback to manual feed list if needed
        if not feeds:
            # You could add a default feed list here or read from a file
            print("⚠️ No feeds configured. Use --add-feed to configure feeds first.")
            return
        
        rss_ingestor = get_unified_rss_ingestor(config)
        results = rss_ingestor.poll_feeds(feeds)
        
        print(f"✅ Polling completed:")
        print(f"   📡 Feeds processed: {results['feeds_processed']}")
        print(f"   ✅ Successful feeds: {results['feeds_successful']}")
        if results.get('errors'):
            print(f"   ❌ Errors: {len(results['errors'])}")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"      • {error}")
        
        rss_ingestor.close()

    # Ad detection and removal commands
    if args.process_audio:
        print(f"🎵 Processing audio with ad detection and removal: {args.process_audio}")
        ad_processor = get_podcast_ad_processor()
        
        # Extract filename for title
        title = args.process_audio.split('/')[-1].split('?')[0]
        
        result = ad_processor.process_podcast_episode(
            audio_url=args.process_audio,
            title=title,
            show_name="Manual Processing"
        )
        
        if result.success:
            print("✅ Audio processing completed successfully")
            print(f"   📁 Original file: {result.original_file_path}")
            print(f"   🧹 Cleaned file: {result.cleaned_file_path}")
            print(f"   📝 Transcript: {result.transcript_file_path}")
            print(f"   📊 Ads detected: {result.ads_detected}")
            print(f"   ⏱️  Time saved: {result.ads_removed_duration:.1f}s")
            print(f"   ⚡ Processing time: {result.processing_time:.1f}s")
        else:
            print("❌ Audio processing failed")
            print(f"   Error: {result.error_message}")
            
        ad_processor.close()
    
    if args.ad_stats:
        print("📊 Ad processing statistics:")
        ad_processor = get_podcast_ad_processor()
        stats = ad_processor.get_processing_statistics()
        
        if 'error' in stats:
            print(f"   ❌ Error retrieving stats: {stats['error']}")
        else:
            print(f"   📈 Total episodes: {stats.get('total_episodes', 0)}")
            print(f"   🎵 Ad processed: {stats.get('ad_processed_episodes', 0)}")
            print(f"   🧹 Cleaned episodes: {stats.get('cleaned_episodes', 0)}")
            print(f"   📊 Processing rate: {stats.get('processing_rate', 0)}%")
            print(f"   🗄️  Database enabled: {stats.get('database_enabled', False)}")
            
        ad_processor.close()
    
    if args.batch_process_ads:
        print(f"🎵 Batch processing episodes from: {args.batch_process_ads}")
        try:
            import json
            with open(args.batch_process_ads, 'r') as f:
                episodes = json.load(f)
            
            ad_processor = get_podcast_ad_processor()
            results = ad_processor.process_multiple_episodes(episodes)
            
            successful = sum(1 for r in results if r.success)
            total = len(results)
            
            print(f"✅ Batch processing completed: {successful}/{total} episodes successful")
            
            # Show summary
            total_ads = sum(r.ads_detected for r in results if r.success)
            total_time_saved = sum(r.ads_removed_duration or 0 for r in results if r.success)
            
            print(f"   📊 Total ads detected: {total_ads}")
            print(f"   ⏱️  Total time saved: {total_time_saved:.1f}s")
            
            ad_processor.close()
            
        except FileNotFoundError:
            print(f"❌ File not found: {args.batch_process_ads}")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON format in: {args.batch_process_ads}")
        except Exception as e:
            print(f"❌ Batch processing failed: {e}")

    if args.instapaper_csv:
        print(f"📖 Processing Instapaper CSV: {args.instapaper_csv}")
        process_instapaper_csv(args.instapaper_csv)

    if args.urls:
        print(f"🔗 Processing URLs from: {args.urls}")
        process_url_file(args.urls)

    if args.recategorize:
        print("🏷️ Recategorizing content...")
        recategorize_all_content()

    if args.cognitive_analysis:
        print("🧠 Running cognitive analysis...")
        # TODO: Implement unified cognitive analysis
        print("   Cognitive analysis integration coming soon...")

    if args.analyze_episode:
        print(f"🧠 Analyzing episode {args.analyze_episode}...")
        # TODO: Implement episode-specific cognitive analysis
        print("   Episode cognitive analysis integration coming soon...")

    if args.all:
        print("🚀 Running all processing types...")
        
        # Run Atlas processing
        fetch_and_save_articles()
        ingest_youtube_history()
        
        # Run podcast processing
        if is_podcast_processing_enabled(config):
            feeds = get_podcast_feeds(config)
            if feeds:
                unified_processor.poll_podcast_feeds(feeds)
        else:
            from helpers.podcast_ingestor import ingest_podcasts
            ingest_podcasts()
        
        # Run cognitive analysis
        if config.cognitive_analysis_enabled:
            print("🧠 Cognitive analysis integration coming soon...")

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n🔗 Integration Status:")
        print(f"   Atlas cognitive features: {'✅ Active' if config.cognitive_analysis_enabled else '❌ Disabled'}")
        print(f"   Podemos podcast processing: {'✅ Active' if config.podcast_processing_enabled else '❌ Disabled'}")
        print(f"   Integration mode: {config.integration_mode}")
        print("\n📚 Quick Start:")
        print("   --serve          Start integrated web dashboard")
        print("   --podcasts       Process podcasts with advanced features")
        print("   --articles       Process articles")
        print("   --all            Process all content types")
        print("\n📡 RSS & Podcast Commands:")
        print("   --rss-ingest URL     Ingest specific RSS feed with unified system")
        print("   --rss-poll-feeds     Poll all configured feeds with unified system")  
        print("   --rss-stats          Show unified RSS processing statistics")
        print("   --add-feed URL       Add new podcast feed to configuration")
        print("\n🎵 Ad Detection & Removal Commands:")
        print("   --process-audio URL  Process audio with advanced ad detection and removal")
        print("   --ad-stats           Show ad processing statistics and performance metrics")
        print("   --batch-process-ads  Batch process multiple episodes from JSON file")

if __name__ == "__main__":
    main()