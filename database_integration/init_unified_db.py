#!/usr/bin/env python3
"""
Atlas-Podemos Database Integration - Database Initialization

Creates the unified database schema that supports both Atlas and Podemos functionality.
This script initializes the database with proper tables, indexes, and constraints.

Usage:
    python3 database_integration/init_unified_db.py [--db-path PATH]
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import sqlite3

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("SQLAlchemy not found. Please run 'pip install sqlalchemy'")
    sys.exit(1)

def create_unified_database_schema(db_path: str = "atlas_unified.db"):
    """
    Create the unified database schema for Atlas-Podemos integration.
    
    Args:
        db_path: Path to the database file to create
    """
    
    print("🚀 ATLAS-PODEMOS DATABASE INTEGRATION")
    print("=" * 60)
    print(f"📁 Database path: {db_path}")
    
    # Create database engine
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    
    # SQL for unified schema
    schema_sql = """
    -- =============================================================================
    -- ATLAS-PODEMOS UNIFIED DATABASE SCHEMA
    -- =============================================================================
    -- Version: 1.0
    -- Date: 2025-08-06
    -- Purpose: Unified schema supporting both Atlas and Podemos functionality
    
    PRAGMA foreign_keys = ON;
    PRAGMA journal_mode = WAL;
    
    -- Main content table (unified for all content types)
    CREATE TABLE IF NOT EXISTS content_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid VARCHAR(32) UNIQUE NOT NULL,          -- Atlas UID system
        content_type VARCHAR(50) NOT NULL,        -- article, podcast, youtube, etc.
        source_url VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        status VARCHAR DEFAULT 'pending',         -- Unified status system
        
        -- Atlas compatibility
        file_path_html VARCHAR,                   -- Path to HTML file
        file_path_markdown VARCHAR,               -- Path to Markdown file  
        file_path_metadata VARCHAR,               -- Path to JSON metadata
        
        -- Podemos compatibility  
        source_guid VARCHAR,                      -- RSS GUID for podcasts
        show_name VARCHAR,                        -- For podcast episodes
        pub_date DATETIME,
        
        -- Common metadata
        description TEXT,
        image_url VARCHAR,
        author VARCHAR,
        tags_json TEXT,                          -- JSON array of tags
        
        -- Processing tracking
        retry_count INTEGER DEFAULT 0,
        last_error TEXT,
        processing_started_at DATETIME,
        processing_completed_at DATETIME,
        
        -- Timestamps
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Indexes for content_items
    CREATE INDEX IF NOT EXISTS idx_content_type ON content_items (content_type);
    CREATE INDEX IF NOT EXISTS idx_status ON content_items (status);
    CREATE INDEX IF NOT EXISTS idx_uid ON content_items (uid);
    CREATE INDEX IF NOT EXISTS idx_source_guid ON content_items (source_guid);
    CREATE INDEX IF NOT EXISTS idx_created_at ON content_items (created_at);
    CREATE INDEX IF NOT EXISTS idx_show_name ON content_items (show_name);
    
    -- Podcast-specific extended data
    CREATE TABLE IF NOT EXISTS podcast_episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_item_id INTEGER NOT NULL,
        
        -- Audio processing
        original_audio_url VARCHAR NOT NULL,
        original_file_path VARCHAR,
        original_duration FLOAT,
        original_file_size INTEGER,
        cleaned_file_path VARCHAR,
        cleaned_duration FLOAT, 
        cleaned_file_size INTEGER,
        cleaned_ready_at DATETIME,
        
        -- Show metadata
        show_image_url VARCHAR,
        show_author VARCHAR,
        
        -- Processing data
        ad_segments_json TEXT,
        transcript_json TEXT,
        fast_transcript_json TEXT,
        cleaned_chapters_json TEXT,
        chapters_json TEXT,
        md_transcript_file_path VARCHAR,
        
        FOREIGN KEY (content_item_id) REFERENCES content_items (id) ON DELETE CASCADE
    );
    
    -- Indexes for podcast_episodes
    CREATE INDEX IF NOT EXISTS idx_podcast_content_item ON podcast_episodes (content_item_id);
    CREATE INDEX IF NOT EXISTS idx_podcast_audio_url ON podcast_episodes (original_audio_url);
    CREATE INDEX IF NOT EXISTS idx_podcast_duration ON podcast_episodes (original_duration);
    
    -- Processing jobs (unified scheduler)
    CREATE TABLE IF NOT EXISTS processing_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_type VARCHAR(50) NOT NULL,            -- ingest, transcribe, analyze, etc.
        content_item_id INTEGER,                  -- Optional: specific content
        command TEXT NOT NULL,
        schedule_expression VARCHAR,              -- Cron expression or interval
        status VARCHAR DEFAULT 'scheduled',
        
        -- Job execution
        last_run_at DATETIME,
        next_run_at DATETIME,
        run_count INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        last_error TEXT,
        
        -- Job configuration
        enabled BOOLEAN DEFAULT TRUE,
        priority INTEGER DEFAULT 0,
        timeout_seconds INTEGER DEFAULT 3600,
        
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (content_item_id) REFERENCES content_items (id) ON DELETE SET NULL
    );
    
    -- Indexes for processing_jobs
    CREATE INDEX IF NOT EXISTS idx_job_type ON processing_jobs (job_type);
    CREATE INDEX IF NOT EXISTS idx_job_status ON processing_jobs (status);
    CREATE INDEX IF NOT EXISTS idx_next_run ON processing_jobs (next_run_at);
    CREATE INDEX IF NOT EXISTS idx_job_enabled ON processing_jobs (enabled);
    
    -- Content relationships and analysis
    CREATE TABLE IF NOT EXISTS content_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_item_id INTEGER NOT NULL,
        analysis_type VARCHAR(50) NOT NULL,      -- cognitive, pattern, similarity
        analysis_data_json TEXT,                 -- Analysis results
        confidence_score FLOAT,
        model_version VARCHAR(50),               -- Track model used for analysis
        
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (content_item_id) REFERENCES content_items (id) ON DELETE CASCADE
    );
    
    -- Indexes for content_analysis
    CREATE INDEX IF NOT EXISTS idx_content_analysis ON content_analysis (content_item_id, analysis_type);
    CREATE INDEX IF NOT EXISTS idx_analysis_type ON content_analysis (analysis_type);
    CREATE INDEX IF NOT EXISTS idx_analysis_confidence ON content_analysis (confidence_score);
    
    -- Content tags (normalized for better querying)
    CREATE TABLE IF NOT EXISTS content_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_item_id INTEGER NOT NULL,
        tag VARCHAR(100) NOT NULL,
        tag_type VARCHAR(50) DEFAULT 'manual',   -- manual, auto, cognitive
        confidence_score FLOAT DEFAULT 1.0,
        
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (content_item_id) REFERENCES content_items (id) ON DELETE CASCADE,
        UNIQUE(content_item_id, tag, tag_type)
    );
    
    -- Indexes for content_tags  
    CREATE INDEX IF NOT EXISTS idx_content_tags ON content_tags (content_item_id);
    CREATE INDEX IF NOT EXISTS idx_tag_name ON content_tags (tag);
    CREATE INDEX IF NOT EXISTS idx_tag_type ON content_tags (tag_type);
    
    -- System metadata and configuration
    CREATE TABLE IF NOT EXISTS system_metadata (
        key VARCHAR(100) PRIMARY KEY,
        value TEXT,
        description TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Insert initial system metadata
    INSERT OR REPLACE INTO system_metadata (key, value, description) VALUES 
        ('schema_version', '1.0', 'Database schema version'),
        ('created_at', datetime('now'), 'Database creation timestamp'),
        ('migration_status', 'initialized', 'Current migration status'),
        ('atlas_integration', 'enabled', 'Atlas integration status'),
        ('podemos_integration', 'enabled', 'Podemos integration status');
    
    -- Create triggers for updated_at timestamps
    CREATE TRIGGER IF NOT EXISTS update_content_items_timestamp 
        AFTER UPDATE ON content_items
        FOR EACH ROW 
        BEGIN
            UPDATE content_items SET updated_at = datetime('now') WHERE id = NEW.id;
        END;
    
    CREATE TRIGGER IF NOT EXISTS update_processing_jobs_timestamp 
        AFTER UPDATE ON processing_jobs
        FOR EACH ROW 
        BEGIN
            UPDATE processing_jobs SET updated_at = datetime('now') WHERE id = NEW.id;
        END;
    
    CREATE TRIGGER IF NOT EXISTS update_system_metadata_timestamp 
        AFTER UPDATE ON system_metadata
        FOR EACH ROW 
        BEGIN
            UPDATE system_metadata SET updated_at = datetime('now') WHERE key = NEW.key;
        END;
    """
    
    try:
        # Execute schema creation
        print("🔧 Creating unified database schema...")
        
        with engine.connect() as connection:
            # Split and execute each statement
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        connection.execute(text(statement + ';'))
                        if i % 10 == 0:  # Progress indicator
                            print(f"   📊 Executed {i+1}/{len(statements)} statements...")
                    except Exception as e:
                        print(f"   ⚠️  Warning on statement {i+1}: {e}")
                        continue
            
            connection.commit()
        
        print("✅ Database schema created successfully!")
        
        # Verify database structure
        verify_database_structure(engine)
        
        print(f"\n🎯 Database initialization complete!")
        print(f"📁 Database file: {os.path.abspath(db_path)}")
        print(f"📊 Schema version: 1.0")
        print(f"🔗 Ready for Atlas-Podemos integration")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def verify_database_structure(engine):
    """Verify the database was created correctly"""
    
    print("\n🔍 Verifying database structure...")
    
    expected_tables = [
        'content_items',
        'podcast_episodes', 
        'processing_jobs',
        'content_analysis',
        'content_tags',
        'system_metadata'
    ]
    
    try:
        with engine.connect() as connection:
            # Check tables exist
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"   📋 Tables found: {len(tables)}")
            
            missing_tables = [table for table in expected_tables if table not in tables]
            if missing_tables:
                print(f"   ❌ Missing tables: {missing_tables}")
                return False
            
            # Check indexes exist
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='index';"))
            indexes = [row[0] for row in result.fetchall()]
            print(f"   🔍 Indexes created: {len(indexes)}")
            
            # Check triggers exist
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='trigger';"))
            triggers = [row[0] for row in result.fetchall()]
            print(f"   ⚡ Triggers created: {len(triggers)}")
            
            # Check system metadata
            result = connection.execute(text("SELECT COUNT(*) FROM system_metadata;"))
            metadata_count = result.fetchone()[0]
            print(f"   ⚙️  System metadata entries: {metadata_count}")
            
            print("   ✅ Database structure verification passed!")
            return True
            
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Initialize unified Atlas-Podemos database"
    )
    parser.add_argument(
        "--db-path", 
        default="atlas_unified.db",
        help="Path to database file (default: atlas_unified.db)"
    )
    parser.add_argument(
        "--force",
        action="store_true", 
        help="Force overwrite existing database"
    )
    
    args = parser.parse_args()
    
    # Check if database already exists
    if os.path.exists(args.db_path) and not args.force:
        response = input(f"Database {args.db_path} already exists. Overwrite? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Database initialization cancelled.")
            return False
    
    # Create the database
    success = create_unified_database_schema(args.db_path)
    
    if success:
        print(f"\n🎉 SUCCESS: Unified database created at {args.db_path}")
        print("📝 Next steps:")
        print("   1. Run migration scripts to import existing data")
        print("   2. Test database with Atlas and Podemos modules")
        print("   3. Update application code to use unified database")
        return True
    else:
        print("\n❌ FAILED: Database initialization failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)