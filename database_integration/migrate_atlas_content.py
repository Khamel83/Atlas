#!/usr/bin/env python3
"""
Atlas Content Migration Script

Migrates existing Atlas file-based content into the unified database.
Imports HTML, Markdown, and JSON metadata files into the content_items table.

Usage:
    python3 database_integration/migrate_atlas_content.py [--db-path PATH] [--atlas-path PATH]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import hashlib
import sqlite3

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
except ImportError:
    print("SQLAlchemy not found. Please run 'pip install sqlalchemy'")
    sys.exit(1)

class AtlasContentMigrator:
    """Migrates Atlas file-based content to unified database"""
    
    def __init__(self, db_path: str, atlas_path: str = "."):
        self.db_path = db_path
        self.atlas_path = Path(atlas_path)
        
        # Atlas directory structure
        self.output_dir = self.atlas_path / "output" / "articles"
        self.html_dir = self.output_dir / "html"
        self.markdown_dir = self.output_dir / "markdown" 
        self.metadata_dir = self.output_dir / "metadata"
        
        # Database connection
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Migration stats
        self.stats = {
            'total_files': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'skipped_existing': 0,
            'errors': []
        }
    
    def migrate_all_content(self) -> bool:
        """Migrate all Atlas content to database"""
        
        print("🔄 ATLAS CONTENT MIGRATION")
        print("=" * 60)
        print(f"📁 Atlas path: {self.atlas_path}")
        print(f"📁 Database: {self.db_path}")
        
        if not self._validate_directories():
            return False
        
        if not self._validate_database():
            return False
        
        # Discover all content files
        content_files = self._discover_content_files()
        if not content_files:
            print("❌ No Atlas content files found to migrate")
            return False
        
        self.stats['total_files'] = len(content_files)
        print(f"📊 Found {len(content_files)} content items to migrate")
        
        # Migrate each content item
        with self.SessionLocal() as session:
            for i, content_info in enumerate(content_files, 1):
                try:
                    success = self._migrate_single_content(session, content_info)
                    if success:
                        self.stats['successful_migrations'] += 1
                    else:
                        self.stats['failed_migrations'] += 1
                    
                    # Progress indicator
                    if i % 50 == 0 or i == len(content_files):
                        progress = (i / len(content_files)) * 100
                        print(f"   📊 Progress: {i}/{len(content_files)} ({progress:.1f}%)")
                
                except Exception as e:
                    self.stats['failed_migrations'] += 1
                    self.stats['errors'].append(f"Error migrating {content_info['uid']}: {e}")
                    continue
            
            session.commit()
        
        self._print_migration_summary()
        return self.stats['failed_migrations'] == 0
    
    def _validate_directories(self) -> bool:
        """Validate Atlas directory structure exists"""
        
        required_dirs = [self.html_dir, self.markdown_dir, self.metadata_dir]
        
        for directory in required_dirs:
            if not directory.exists():
                print(f"❌ Atlas directory not found: {directory}")
                return False
                
        print("✅ Atlas directory structure validated")
        return True
    
    def _validate_database(self) -> bool:
        """Validate unified database exists and has correct schema"""
        
        if not os.path.exists(self.db_path):
            print(f"❌ Database not found: {self.db_path}")
            print("   Run init_unified_db.py first to create the database")
            return False
        
        try:
            with self.engine.connect() as connection:
                # Check for required tables
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='content_items';"))
                if not result.fetchone():
                    print("❌ content_items table not found in database")
                    return False
                    
                print("✅ Database schema validated")
                return True
                
        except Exception as e:
            print(f"❌ Database validation failed: {e}")
            return False
    
    def _discover_content_files(self) -> list:
        """Discover all Atlas content files by scanning metadata directory"""
        
        print("🔍 Discovering Atlas content files...")
        
        content_files = []
        
        if not self.metadata_dir.exists():
            return content_files
        
        for metadata_file in self.metadata_dir.glob("*.json"):
            uid = metadata_file.stem
            
            # Check for corresponding HTML and Markdown files
            html_file = self.html_dir / f"{uid}.html"
            markdown_file = self.markdown_dir / f"{uid}.md"
            
            content_info = {
                'uid': uid,
                'metadata_path': str(metadata_file),
                'html_path': str(html_file) if html_file.exists() else None,
                'markdown_path': str(markdown_file) if markdown_file.exists() else None,
            }
            
            content_files.append(content_info)
        
        return content_files
    
    def _migrate_single_content(self, session: Session, content_info: dict) -> bool:
        """Migrate a single content item to database"""
        
        uid = content_info['uid']
        
        # Check if already exists
        existing = session.execute(
            text("SELECT id FROM content_items WHERE uid = :uid"),
            {'uid': uid}
        ).fetchone()
        
        if existing:
            self.stats['skipped_existing'] += 1
            return True
        
        # Load metadata
        try:
            with open(content_info['metadata_path'], 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            self.stats['errors'].append(f"Failed to load metadata for {uid}: {e}")
            return False
        
        # Extract data for database
        content_data = self._extract_content_data(metadata, content_info)
        
        # Insert into database
        try:
            insert_sql = text("""
                INSERT INTO content_items (
                    uid, content_type, source_url, title, status,
                    file_path_html, file_path_markdown, file_path_metadata,
                    description, image_url, author, tags_json,
                    retry_count, last_error,
                    created_at, updated_at
                ) VALUES (
                    :uid, :content_type, :source_url, :title, :status,
                    :file_path_html, :file_path_markdown, :file_path_metadata,
                    :description, :image_url, :author, :tags_json,
                    :retry_count, :last_error,
                    :created_at, :updated_at
                )
            """)
            
            session.execute(insert_sql, content_data)
            return True
            
        except Exception as e:
            self.stats['errors'].append(f"Database insert failed for {uid}: {e}")
            return False
    
    def _extract_content_data(self, metadata: dict, content_info: dict) -> dict:
        """Extract database fields from Atlas metadata"""
        
        # Determine content type from metadata or file paths
        content_type = metadata.get('content_type', 'article')
        if 'instapaper' in content_type.lower():
            content_type = 'article'
        elif 'youtube' in content_type.lower():
            content_type = 'youtube'
        elif 'podcast' in content_type.lower():
            content_type = 'podcast'
        
        # Extract status
        status = 'completed' if metadata.get('status') == 'success' else 'error'
        if metadata.get('error'):
            status = 'error'
        
        # Extract timestamps
        created_at = metadata.get('created_at') or datetime.now().isoformat()
        updated_at = metadata.get('updated_at') or datetime.now().isoformat()
        
        # Convert timestamps to SQLite format if needed
        try:
            if 'T' in created_at:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            if 'T' in updated_at:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
        except:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract tags
        tags = metadata.get('tags', [])
        tags_json = json.dumps(tags) if tags else None
        
        return {
            'uid': content_info['uid'],
            'content_type': content_type,
            'source_url': metadata.get('source', '') or '',
            'title': metadata.get('title', 'Untitled'),
            'status': status,
            'file_path_html': content_info['html_path'],
            'file_path_markdown': content_info['markdown_path'],
            'file_path_metadata': content_info['metadata_path'],
            'description': self._truncate_text(metadata.get('description', ''), 5000),
            'image_url': metadata.get('image_url'),
            'author': metadata.get('author'),
            'tags_json': tags_json,
            'retry_count': 0,
            'last_error': metadata.get('error'),
            'created_at': created_at,
            'updated_at': updated_at
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
        print(f"  📁 Total files found: {self.stats['total_files']}")
        print(f"  ✅ Successfully migrated: {self.stats['successful_migrations']}")
        print(f"  ⏭️  Skipped (already exists): {self.stats['skipped_existing']}")
        print(f"  ❌ Failed migrations: {self.stats['failed_migrations']}")
        
        if self.stats['errors']:
            print(f"\n🚨 ERRORS ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                print(f"    • {error}")
            
            if len(self.stats['errors']) > 10:
                print(f"    ... and {len(self.stats['errors']) - 10} more errors")
        
        success_rate = (self.stats['successful_migrations'] / self.stats['total_files']) * 100 if self.stats['total_files'] > 0 else 0
        print(f"\n🎯 Success rate: {success_rate:.1f}%")
        
        if self.stats['failed_migrations'] == 0:
            print("🎉 All Atlas content migrated successfully!")
        else:
            print(f"⚠️  {self.stats['failed_migrations']} items failed migration")

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Migrate Atlas content to unified database"
    )
    parser.add_argument(
        "--db-path",
        default="atlas_unified.db",
        help="Path to unified database (default: atlas_unified.db)"
    )
    parser.add_argument(
        "--atlas-path",
        default=".",
        help="Path to Atlas directory (default: current directory)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.db_path):
        print(f"❌ Database not found: {args.db_path}")
        print("   Run init_unified_db.py first to create the unified database")
        return False
    
    atlas_path = Path(args.atlas_path)
    if not atlas_path.exists():
        print(f"❌ Atlas path not found: {atlas_path}")
        return False
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        # TODO: Implement dry run functionality
        print("   Dry run not implemented yet")
        return True
    
    # Run migration
    migrator = AtlasContentMigrator(args.db_path, args.atlas_path)
    success = migrator.migrate_all_content()
    
    if success:
        print(f"\n🎉 SUCCESS: Atlas content migrated to {args.db_path}")
        return True
    else:
        print(f"\n❌ MIGRATION FAILED: Check errors above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)