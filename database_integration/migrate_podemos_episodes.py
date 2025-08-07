#!/usr/bin/env python3
"""
Podemos Episode Migration Script

Migrates existing Podemos episodes from the current SQLite database to the unified schema.
Imports episode data from the episodes table into both content_items and podcast_episodes tables.

Usage:
    python3 database_integration/migrate_podemos_episodes.py [--unified-db PATH] [--podemos-db PATH]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import sqlite3
import hashlib

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
except ImportError:
    print("SQLAlchemy not found. Please run 'pip install sqlalchemy'")
    sys.exit(1)

class PodemosEpisodeMigrator:
    """Migrates Podemos episodes to unified database"""
    
    def __init__(self, unified_db_path: str, podemos_db_path: str = None):
        self.unified_db_path = unified_db_path
        self.podemos_db_path = podemos_db_path or self._find_podemos_db()
        
        # Database connections
        self.unified_engine = create_engine(f'sqlite:///{unified_db_path}', echo=False)
        self.UnifiedSession = sessionmaker(bind=self.unified_engine)
        
        # Migration stats
        self.stats = {
            'total_episodes': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'skipped_existing': 0,
            'errors': []
        }
    
    def migrate_all_episodes(self) -> bool:
        """Migrate all Podemos episodes to unified database"""
        
        print("🔄 PODEMOS EPISODE MIGRATION")
        print("=" * 60)
        print(f"📁 Podemos DB: {self.podemos_db_path}")
        print(f"📁 Unified DB: {self.unified_db_path}")
        
        if not self._validate_databases():
            return False
        
        # Load episodes from Podemos database
        episodes = self._load_podemos_episodes()
        if not episodes:
            print("❌ No Podemos episodes found to migrate")
            return False
        
        self.stats['total_episodes'] = len(episodes)
        print(f"📊 Found {len(episodes)} episodes to migrate")
        
        # Migrate each episode
        with self.UnifiedSession() as session:
            for i, episode in enumerate(episodes, 1):
                try:
                    success = self._migrate_single_episode(session, episode)
                    if success:
                        self.stats['successful_migrations'] += 1
                    else:
                        self.stats['failed_migrations'] += 1
                    
                    # Progress indicator
                    if i % 25 == 0 or i == len(episodes):
                        progress = (i / len(episodes)) * 100
                        print(f"   📊 Progress: {i}/{len(episodes)} ({progress:.1f}%)")
                
                except Exception as e:
                    self.stats['failed_migrations'] += 1
                    self.stats['errors'].append(f"Error migrating episode {episode.get('source_guid', 'unknown')}: {e}")
                    continue
            
            session.commit()
        
        self._print_migration_summary()
        return self.stats['failed_migrations'] == 0
    
    def _find_podemos_db(self) -> str:
        """Find Podemos database file"""
        
        # Common paths for Podemos database
        possible_paths = [
            "db.sqlite3",
            "podcast_processing/db.sqlite3",
            "podemos.db",
            "podcast_processing/podemos.db"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ Found Podemos database: {path}")
                return path
        
        print("❌ Podemos database not found in common locations")
        print("   Please specify path with --podemos-db")
        return None
    
    def _validate_databases(self) -> bool:
        """Validate both databases exist and have correct schema"""
        
        # Check unified database
        if not os.path.exists(self.unified_db_path):
            print(f"❌ Unified database not found: {self.unified_db_path}")
            print("   Run init_unified_db.py first to create the database")
            return False
        
        # Check Podemos database
        if not self.podemos_db_path or not os.path.exists(self.podemos_db_path):
            print(f"❌ Podemos database not found: {self.podemos_db_path}")
            return False
        
        try:
            # Validate unified database schema
            with self.unified_engine.connect() as connection:
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='content_items';"))
                if not result.fetchone():
                    print("❌ content_items table not found in unified database")
                    return False
                
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='podcast_episodes';"))
                if not result.fetchone():
                    print("❌ podcast_episodes table not found in unified database")
                    return False
            
            # Validate Podemos database schema
            podemos_conn = sqlite3.connect(self.podemos_db_path)
            cursor = podemos_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='episodes';")
            if not cursor.fetchone():
                print("❌ episodes table not found in Podemos database")
                podemos_conn.close()
                return False
            podemos_conn.close()
            
            print("✅ Database schemas validated")
            return True
            
        except Exception as e:
            print(f"❌ Database validation failed: {e}")
            return False
    
    def _load_podemos_episodes(self) -> list:
        """Load all episodes from Podemos database"""
        
        print("🔍 Loading Podemos episodes...")
        
        try:
            conn = sqlite3.connect(self.podemos_db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM episodes 
                ORDER BY pub_date DESC
            """)
            
            episodes = []
            for row in cursor.fetchall():
                episodes.append(dict(row))
            
            conn.close()
            
            print(f"   📊 Loaded {len(episodes)} episodes")
            return episodes
            
        except Exception as e:
            print(f"❌ Failed to load Podemos episodes: {e}")
            return []
    
    def _migrate_single_episode(self, session: Session, episode: dict) -> bool:
        """Migrate a single episode to unified schema"""
        
        source_guid = episode.get('source_guid')
        
        # Generate UID for content_items (based on source_guid)
        uid = hashlib.md5(f"podemos_episode_{source_guid}".encode()).hexdigest()
        
        # Check if already exists in content_items
        existing = session.execute(
            text("SELECT id FROM content_items WHERE uid = :uid OR source_guid = :source_guid"),
            {'uid': uid, 'source_guid': source_guid}
        ).fetchone()
        
        if existing:
            self.stats['skipped_existing'] += 1
            return True
        
        # Extract data for content_items
        content_data = self._extract_content_data(episode, uid)
        
        # Extract data for podcast_episodes
        podcast_data = self._extract_podcast_data(episode)
        
        try:
            # Insert into content_items first
            content_insert_sql = text("""
                INSERT INTO content_items (
                    uid, content_type, source_url, title, status,
                    source_guid, show_name, pub_date,
                    description, image_url, author, tags_json,
                    retry_count, last_error,
                    created_at, updated_at
                ) VALUES (
                    :uid, :content_type, :source_url, :title, :status,
                    :source_guid, :show_name, :pub_date,
                    :description, :image_url, :author, :tags_json,
                    :retry_count, :last_error,
                    :created_at, :updated_at
                )
            """)
            
            result = session.execute(content_insert_sql, content_data)
            content_item_id = result.lastrowid
            
            # Insert into podcast_episodes
            podcast_data['content_item_id'] = content_item_id
            
            podcast_insert_sql = text("""
                INSERT INTO podcast_episodes (
                    content_item_id, original_audio_url, original_file_path,
                    original_duration, original_file_size, cleaned_file_path,
                    cleaned_duration, cleaned_file_size, cleaned_ready_at,
                    show_image_url, show_author, ad_segments_json,
                    transcript_json, fast_transcript_json, cleaned_chapters_json,
                    chapters_json, md_transcript_file_path
                ) VALUES (
                    :content_item_id, :original_audio_url, :original_file_path,
                    :original_duration, :original_file_size, :cleaned_file_path,
                    :cleaned_duration, :cleaned_file_size, :cleaned_ready_at,
                    :show_image_url, :show_author, :ad_segments_json,
                    :transcript_json, :fast_transcript_json, :cleaned_chapters_json,
                    :chapters_json, :md_transcript_file_path
                )
            """)
            
            session.execute(podcast_insert_sql, podcast_data)
            return True
            
        except Exception as e:
            self.stats['errors'].append(f"Database insert failed for {source_guid}: {e}")
            return False
    
    def _extract_content_data(self, episode: dict, uid: str) -> dict:
        """Extract content_items data from Podemos episode"""
        
        # Map Podemos status to unified status
        status_mapping = {
            'pending_download': 'pending',
            'downloaded': 'processing',
            'pending_cut': 'processing',
            'cut': 'processing', 
            'pending_transcribe': 'processing',
            'transcribed': 'completed',
            'error': 'error'
        }
        
        podemos_status = episode.get('status', 'pending')
        unified_status = status_mapping.get(podemos_status, 'pending')
        
        # Convert timestamps
        pub_date = episode.get('pub_date')
        if isinstance(pub_date, str):
            try:
                # Convert ISO format to SQLite format
                dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                pub_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pub_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif pub_date:
            pub_date = str(pub_date)
        else:
            pub_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate tags from show_name
        show_name = episode.get('show_name', '')
        tags = [show_name, 'podcast'] if show_name else ['podcast']
        
        return {
            'uid': uid,
            'content_type': 'podcast',
            'source_url': episode.get('original_audio_url', ''),
            'title': episode.get('title', 'Untitled Episode'),
            'status': unified_status,
            'source_guid': episode.get('source_guid'),
            'show_name': episode.get('show_name'),
            'pub_date': pub_date,
            'description': self._truncate_text(episode.get('description'), 5000),
            'image_url': episode.get('image_url'),
            'author': episode.get('show_author'),
            'tags_json': json.dumps(tags),
            'retry_count': episode.get('retry_count', 0),
            'last_error': episode.get('last_error'),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _extract_podcast_data(self, episode: dict) -> dict:
        """Extract podcast_episodes data from Podemos episode"""
        
        # Convert cleaned_ready_at timestamp
        cleaned_ready_at = episode.get('cleaned_ready_at')
        if isinstance(cleaned_ready_at, str) and cleaned_ready_at:
            try:
                dt = datetime.fromisoformat(cleaned_ready_at.replace('Z', '+00:00'))
                cleaned_ready_at = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                cleaned_ready_at = None
        elif cleaned_ready_at:
            cleaned_ready_at = str(cleaned_ready_at)
        else:
            cleaned_ready_at = None
        
        return {
            'original_audio_url': episode.get('original_audio_url', ''),
            'original_file_path': episode.get('original_file_path'),
            'original_duration': episode.get('original_duration'),
            'original_file_size': episode.get('original_file_size'),
            'cleaned_file_path': episode.get('cleaned_file_path'),
            'cleaned_duration': episode.get('cleaned_duration'),
            'cleaned_file_size': episode.get('cleaned_file_size'),
            'cleaned_ready_at': cleaned_ready_at,
            'show_image_url': episode.get('show_image_url'),
            'show_author': episode.get('show_author'),
            'ad_segments_json': episode.get('ad_segments_json'),
            'transcript_json': episode.get('transcript_json'),
            'fast_transcript_json': episode.get('fast_transcript_json'),
            'cleaned_chapters_json': episode.get('cleaned_chapters_json'),
            'chapters_json': episode.get('chapters_json'),
            'md_transcript_file_path': episode.get('md_transcript_file_path')
        }
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length"""
        if not text:
            return None
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _print_migration_summary(self):
        """Print migration summary"""
        
        print(f"\n📊 MIGRATION SUMMARY")
        print("=" * 40)
        print(f"  📁 Total episodes found: {self.stats['total_episodes']}")
        print(f"  ✅ Successfully migrated: {self.stats['successful_migrations']}")
        print(f"  ⏭️  Skipped (already exists): {self.stats['skipped_existing']}")
        print(f"  ❌ Failed migrations: {self.stats['failed_migrations']}")
        
        if self.stats['errors']:
            print(f"\n🚨 ERRORS ({len(self.stats['errors'])}):") 
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                print(f"    • {error}")
            
            if len(self.stats['errors']) > 10:
                print(f"    ... and {len(self.stats['errors']) - 10} more errors")
        
        success_rate = (self.stats['successful_migrations'] / self.stats['total_episodes']) * 100 if self.stats['total_episodes'] > 0 else 0
        print(f"\n🎯 Success rate: {success_rate:.1f}%")
        
        if self.stats['failed_migrations'] == 0:
            print("🎉 All Podemos episodes migrated successfully!")
        else:
            print(f"⚠️  {self.stats['failed_migrations']} episodes failed migration")

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Migrate Podemos episodes to unified database"
    )
    parser.add_argument(
        "--unified-db",
        default="atlas_unified.db",
        help="Path to unified database (default: atlas_unified.db)"
    )
    parser.add_argument(
        "--podemos-db",
        help="Path to Podemos database (default: auto-detect)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    
    args = parser.parse_args()
    
    # Validate unified database exists
    if not os.path.exists(args.unified_db):
        print(f"❌ Unified database not found: {args.unified_db}")
        print("   Run init_unified_db.py first to create the unified database")
        return False
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        # TODO: Implement dry run functionality
        print("   Dry run not implemented yet")
        return True
    
    # Run migration
    migrator = PodemosEpisodeMigrator(args.unified_db, args.podemos_db)
    success = migrator.migrate_all_episodes()
    
    if success:
        print(f"\n🎉 SUCCESS: Podemos episodes migrated to {args.unified_db}")
        return True
    else:
        print(f"\n❌ MIGRATION FAILED: Check errors above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)