# Database Integration Analysis - Atlas + Podemos

*Date: August 6, 2025*  
*Status: Major Task 2.1 - Schema Analysis Complete*

## 🔍 Current Database Architectures

### Atlas Database Architecture
**Storage Strategy**: File-based with minimal database usage
- **SQLite for APScheduler**: `scheduler.db` for job scheduling only
- **Content Storage**: Individual files (HTML/MD/JSON) in filesystem
- **No main application database**: Content metadata stored as JSON sidecars
- **Configuration**: JSON files (`scheduler_jobs.json`, etc.)

**Files Structure**:
```
Atlas/
├── scheduler.db           # APScheduler jobs (SQLite)
├── scheduler_jobs.json    # Job definitions
└── output/articles/
    ├── html/             # Article HTML files
    ├── markdown/         # Article MD files
    └── metadata/         # JSON metadata per article
```

### Podemos Database Architecture
**Storage Strategy**: Centralized SQLite database with SQLAlchemy ORM
- **Main Database**: `db.sqlite3` in media base path
- **SQLAlchemy ORM**: Full object-relational mapping
- **Single Model**: `Episode` model with rich metadata
- **Processing Status**: Tracks full processing pipeline status

**Database Schema**:
```sql
-- Episodes Table
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY,
    source_guid VARCHAR UNIQUE NOT NULL,
    title VARCHAR NOT NULL,
    show_name VARCHAR NOT NULL,
    pub_date DATETIME NOT NULL,
    original_audio_url VARCHAR NOT NULL,
    original_file_path VARCHAR UNIQUE,
    original_duration FLOAT,
    original_file_size INTEGER,
    cleaned_file_path VARCHAR UNIQUE,
    cleaned_duration FLOAT,
    cleaned_file_size INTEGER,
    cleaned_ready_at DATETIME,
    status VARCHAR DEFAULT 'pending_download',
    image_url VARCHAR,
    show_image_url VARCHAR,
    show_author VARCHAR,
    description TEXT,
    ad_segments_json TEXT,
    transcript_json TEXT,
    fast_transcript_json TEXT,
    cleaned_chapters_json TEXT,
    chapters_json TEXT,
    md_transcript_file_path VARCHAR,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);
```

## 🎯 Integration Challenge Analysis

### **Key Differences**:
1. **Storage Philosophy**: Atlas = file-based, Podemos = database-centered
2. **ORM Usage**: Atlas = no ORM, Podemos = SQLAlchemy
3. **Content Management**: Atlas = individual files, Podemos = centralized records
4. **Processing Status**: Atlas = implicit, Podemos = explicit status tracking

### **Compatibility Issues**:
1. **Schema Conflicts**: Different approaches to content storage
2. **File Management**: Atlas expects individual files, Podemos expects database records  
3. **Status Tracking**: Need unified processing status system
4. **Transaction Management**: Atlas has no transactions, Podemos uses sessions

## 🏗️ Unified Database Design

### Design Principles
1. **Backward Compatibility**: Existing Atlas content must work
2. **Processing Status**: Unified status tracking for all content
3. **Content Flexibility**: Support both file-based and database content
4. **Performance**: Optimize for both individual access and batch operations

### Unified Schema Design

```sql
-- Core content table (unified for all content types)
CREATE TABLE content_items (
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
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexing
    INDEX idx_content_type (content_type),
    INDEX idx_status (status),
    INDEX idx_uid (uid),
    INDEX idx_source_guid (source_guid)
);

-- Podcast-specific extended data
CREATE TABLE podcast_episodes (
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
    
    FOREIGN KEY (content_item_id) REFERENCES content_items (id),
    INDEX idx_content_item (content_item_id)
);

-- Processing jobs (unified scheduler)
CREATE TABLE processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type VARCHAR(50) NOT NULL,            -- ingest, transcribe, analyze, etc.
    content_item_id INTEGER,                  -- Optional: specific content
    command TEXT NOT NULL,
    schedule VARCHAR,                         -- Cron expression
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
    
    FOREIGN KEY (content_item_id) REFERENCES content_items (id),
    INDEX idx_job_type (job_type),
    INDEX idx_status (status),
    INDEX idx_next_run (next_run_at)
);

-- Content relationships and analysis
CREATE TABLE content_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_item_id INTEGER NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,      -- cognitive, pattern, similarity
    analysis_data_json TEXT,                 -- Analysis results
    confidence_score FLOAT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (content_item_id) REFERENCES content_items (id),
    INDEX idx_content_analysis (content_item_id, analysis_type)
);
```

## 🔄 Migration Strategy

### Phase 1: Database Setup
1. **Create unified database**: `atlas_unified.db`
2. **Import existing content**: Migrate Atlas files to database records
3. **Migrate Podemos data**: Import episodes into unified schema
4. **Preserve file structure**: Maintain Atlas file-based storage

### Phase 2: Dual-Mode Operation  
1. **Write to both**: New content goes to database AND files
2. **Read from database**: Query database first, fallback to files
3. **Gradual migration**: Move file-based operations to database
4. **Testing**: Ensure all functionality works in dual mode

### Phase 3: Database-Primary
1. **Database becomes source of truth**: All queries use database
2. **Files become cache**: Generated from database when needed
3. **Performance optimization**: Database queries replace file scanning
4. **Cleanup**: Remove redundant file-based code

## 📊 Implementation Tasks

### 2.1 ✅ Analyze Schemas - COMPLETED
- [x] Document Atlas file-based approach
- [x] Document Podemos SQLAlchemy approach  
- [x] Identify integration challenges
- [x] Design unified schema

### 2.2 Design Unified Schema - COMPLETED ABOVE
- [x] Content items table (unified)
- [x] Podcast episodes table (Podemos compatibility)
- [x] Processing jobs table (unified scheduler)
- [x] Content analysis table (Atlas cognitive features)

### 2.3 Create Database Migration Scripts - NEXT
- [ ] Create database initialization script
- [ ] Atlas content import script (files → database)
- [ ] Podemos episode migration script  
- [ ] Data integrity validation script

### 2.4 Implement Unified Database Models - PENDING
- [ ] SQLAlchemy models for unified schema
- [ ] Database connection management
- [ ] Session handling and transactions
- [ ] Model relationships and queries

### 2.5 Test Data Migration and Integrity - PENDING  
- [ ] Test Atlas content import
- [ ] Test Podemos episode migration
- [ ] Validate data relationships
- [ ] Performance testing

### 2.6 Update Database Interactions - PENDING
- [ ] Update Atlas helpers to use database
- [ ] Update Podemos modules for unified schema
- [ ] Implement dual-mode operations
- [ ] Update web dashboard queries

### 2.7 Verify Database Performance - PENDING
- [ ] Query performance testing
- [ ] Index optimization
- [ ] Connection pooling
- [ ] Database size and growth analysis

## 🎯 Success Criteria

**Database Integration Complete When**:
1. ✅ Schemas analyzed and unified design created
2. 🔄 All existing Atlas content accessible via database
3. 🔄 All existing Podemos episodes accessible via unified schema
4. 🔄 No data loss during migration
5. 🔄 Performance equal or better than file-based approach
6. 🔄 All Atlas and Podemos features work with unified database
7. 🔄 Cognitive analysis can operate on all content types

## 🚨 Risk Mitigation

**Data Safety**:
- Create backups before migration
- Implement rollback procedures
- Validate data integrity at each step
- Test with subset of data first

**Performance Concerns**:
- Monitor query performance vs file access
- Implement proper indexing
- Use connection pooling
- Consider read replicas for heavy queries

**Compatibility Issues**:
- Maintain file access for gradual migration
- Implement feature flags for database vs file modes
- Extensive testing of all features
- Monitor for regression issues

---

**STATUS**: Ready for 2.3 - Create Database Migration Scripts  
**NEXT TASK**: Build the database initialization and migration scripts