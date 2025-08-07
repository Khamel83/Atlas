#!/usr/bin/env python3
"""
Test Script for Unified Database Models

Tests the unified database models and connection management to ensure
everything works correctly before integration with Atlas and Podemos.

Usage:
    python3 database_integration/test_models.py
"""

import os
import sys
import tempfile
import hashlib
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from database_integration import (
        UnifiedDB, ContentItem, PodcastEpisode, ProcessingJob,
        ContentAnalysis, ContentTag, SystemMetadata
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the Atlas root directory")
    sys.exit(1)

def test_database_creation():
    """Test database creation and table initialization"""
    print("🧪 Testing database creation...")
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    try:
        # Initialize database
        db = UnifiedDB(temp_db.name)
        
        # Check database info
        info = db.get_database_info()
        print(f"   ✅ Database created: {info['file_size_mb']} MB")
        print(f"   ✅ Content items: {info['content_items']}")
        print(f"   ✅ Podcast episodes: {info['podcast_episodes']}")
        
        db.close()
        return True
        
    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

def test_content_item_operations():
    """Test ContentItem model operations"""
    print("\n🧪 Testing ContentItem operations...")
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    try:
        db = UnifiedDB(temp_db.name)
        
        # Test Atlas article content
        article_uid = hashlib.md5("test_article".encode()).hexdigest()
        article = ContentItem(
            uid=article_uid,
            content_type='article',
            source_url='https://example.com/article',
            title='Test Article',
            status='completed',
            file_path_html='/path/to/article.html',
            file_path_markdown='/path/to/article.md',
            file_path_metadata='/path/to/article.json',
            description='A test article for validation',
            author='Test Author',
            tags=['test', 'article', 'validation']
        )
        
        # Test Podemos podcast content
        podcast_uid = hashlib.md5("test_podcast".encode()).hexdigest()
        podcast = ContentItem(
            uid=podcast_uid,
            content_type='podcast',
            source_url='https://example.com/podcast.mp3',
            title='Test Podcast Episode',
            status='completed',
            source_guid='podcast_guid_123',
            show_name='Test Podcast Show',
            pub_date=datetime.utcnow(),
            description='A test podcast episode',
            author='Podcast Host',
            tags=['podcast', 'test']
        )
        
        # Add content to database
        db.add_content(article)
        db.add_content(podcast)
        
        print(f"   ✅ Added article: {article.title}")
        print(f"   ✅ Added podcast: {podcast.title}")
        
        # Test queries
        all_content = db.get_all_content()
        articles = db.get_articles()
        podcasts = db.get_podcasts()
        
        print(f"   ✅ Total content: {len(all_content)}")
        print(f"   ✅ Articles: {len(articles)}")
        print(f"   ✅ Podcasts: {len(podcasts)}")
        
        # Test lookup functions
        found_article = db.find_content_by_uid(article_uid)
        found_podcast = db.find_content_by_guid('podcast_guid_123')
        
        print(f"   ✅ Found article by UID: {found_article.title if found_article else 'None'}")
        print(f"   ✅ Found podcast by GUID: {found_podcast.title if found_podcast else 'None'}")
        
        # Test properties
        print(f"   ✅ Article is Atlas content: {article.is_atlas_content}")
        print(f"   ✅ Podcast is Podemos content: {podcast.is_podemos_content}")
        print(f"   ✅ Article tags: {article.tags}")
        print(f"   ✅ Podcast tags: {podcast.tags}")
        
        db.close()
        return True
        
    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

def test_podcast_episode_model():
    """Test PodcastEpisode extended model"""
    print("\n🧪 Testing PodcastEpisode model...")
    
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    try:
        db = UnifiedDB(temp_db.name)
        
        with db.session() as session:
            # Create content item
            content = ContentItem(
                uid=hashlib.md5("podcast_test".encode()).hexdigest(),
                content_type='podcast',
                source_url='https://example.com/episode.mp3',
                title='Test Episode with Details',
                status='completed',
                source_guid='episode_123',
                show_name='Technical Podcast'
            )
            session.add(content)
            session.flush()  # Get the ID
            
            # Create podcast episode details
            episode = PodcastEpisode(
                content_item_id=content.id,
                original_audio_url='https://example.com/episode.mp3',
                original_file_path='/media/podcasts/episode.mp3',
                original_duration=3600.0,  # 1 hour
                original_file_size=50000000,  # 50MB
                cleaned_file_path='/media/podcasts/episode_cleaned.mp3',
                cleaned_duration=3300.0,  # 55 minutes after ad removal
                cleaned_file_size=45000000,  # 45MB
                show_author='Tech Host',
                ad_segments=[
                    {'start': 300, 'end': 360, 'type': 'commercial'},
                    {'start': 1800, 'end': 1920, 'type': 'sponsor'}
                ],
                transcript={
                    'segments': [
                        {'start': 0, 'end': 10, 'text': 'Welcome to the show...'}
                    ],
                    'confidence': 0.95
                },
                chapters=[
                    {'start': 0, 'title': 'Introduction'},
                    {'start': 600, 'title': 'Main Topic'}
                ]
            )
            session.add(episode)
            session.commit()
            
            print(f"   ✅ Created podcast episode: {content.title}")
            print(f"   ✅ Original duration: {episode.duration_minutes} minutes")
            print(f"   ✅ File size: {episode.size_mb} MB")
            print(f"   ✅ Ad segments: {len(episode.ad_segments)}")
            print(f"   ✅ Transcript available: {'Yes' if episode.transcript else 'No'}")
            print(f"   ✅ Chapters: {len(episode.chapters)}")
        
        # Test joined queries
        episodes_with_content = db.get_podcast_episodes_with_details()
        print(f"   ✅ Episodes with details: {len(episodes_with_content)}")
        
        # Test show statistics
        shows = db.get_podcast_shows()
        print(f"   ✅ Podcast shows: {shows}")
        
        db.close()
        return True
        
    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

def test_processing_jobs():
    """Test ProcessingJob model"""
    print("\n🧪 Testing ProcessingJob model...")
    
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    try:
        db = UnifiedDB(temp_db.name)
        
        with db.session() as session:
            # Create a content item
            content = ContentItem(
                uid=hashlib.md5("job_test".encode()).hexdigest(),
                content_type='article',
                source_url='https://example.com/article',
                title='Article for Job Test'
            )
            session.add(content)
            session.flush()
            
            # Create processing jobs
            ingest_job = ProcessingJob(
                job_type='ingest',
                content_item_id=content.id,
                command='python3 run.py --ingest',
                schedule_expression='0 10 * * *',  # Daily at 10 AM
                status='scheduled',
                enabled=True,
                priority=1
            )
            
            analyze_job = ProcessingJob(
                job_type='analyze',
                command='python3 scripts/cognitive_analysis.py',
                schedule_expression='0 2 * * 1',  # Weekly on Monday at 2 AM
                status='scheduled',
                enabled=True,
                priority=0
            )
            
            session.add_all([ingest_job, analyze_job])
            session.commit()
            
            print(f"   ✅ Created ingest job: {ingest_job.job_type}")
            print(f"   ✅ Created analyze job: {analyze_job.job_type}")
        
        # Test processing statistics
        stats = db.get_processing_statistics()
        print(f"   ✅ Processing statistics: {stats}")
        
        db.close()
        return True
        
    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

def test_content_analysis_and_tags():
    """Test ContentAnalysis and ContentTag models"""
    print("\n🧪 Testing ContentAnalysis and ContentTag models...")
    
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    try:
        db = UnifiedDB(temp_db.name)
        
        with db.session() as session:
            # Create content item
            content = ContentItem(
                uid=hashlib.md5("analysis_test".encode()).hexdigest(),
                content_type='article',
                source_url='https://example.com/tech-article',
                title='Technical Article for Analysis'
            )
            session.add(content)
            session.flush()
            
            # Create content analysis
            cognitive_analysis = ContentAnalysis(
                content_item_id=content.id,
                analysis_type='cognitive',
                confidence_score=0.87,
                model_version='claude-3.5-sonnet',
                analysis_data={
                    'topics': ['technology', 'artificial intelligence'],
                    'sentiment': 'positive',
                    'complexity': 'medium',
                    'key_concepts': ['machine learning', 'data science']
                }
            )
            
            pattern_analysis = ContentAnalysis(
                content_item_id=content.id,
                analysis_type='pattern',
                confidence_score=0.92,
                analysis_data={
                    'pattern_type': 'tutorial',
                    'structure': 'introduction -> examples -> conclusion'
                }
            )
            
            # Create content tags
            manual_tag = ContentTag(
                content_item_id=content.id,
                tag='technology',
                tag_type='manual',
                confidence_score=1.0
            )
            
            auto_tag = ContentTag(
                content_item_id=content.id,
                tag='artificial-intelligence',
                tag_type='auto',
                confidence_score=0.89
            )
            
            cognitive_tag = ContentTag(
                content_item_id=content.id,
                tag='machine-learning',
                tag_type='cognitive',
                confidence_score=0.94
            )
            
            session.add_all([
                cognitive_analysis, pattern_analysis,
                manual_tag, auto_tag, cognitive_tag
            ])
            session.commit()
            
            print(f"   ✅ Created cognitive analysis: {cognitive_analysis.confidence_score}")
            print(f"   ✅ Created pattern analysis: {pattern_analysis.confidence_score}")
            print(f"   ✅ Analysis data: {cognitive_analysis.analysis_data}")
            print(f"   ✅ Created 3 tags with different types")
        
        db.close()
        return True
        
    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

def test_database_statistics():
    """Test database statistics and reporting"""
    print("\n🧪 Testing database statistics...")
    
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    try:
        db = UnifiedDB(temp_db.name)
        
        # Add some test data
        with db.session() as session:
            # Add multiple content items
            for i in range(5):
                content = ContentItem(
                    uid=hashlib.md5(f"stats_test_{i}".encode()).hexdigest(),
                    content_type='article' if i % 2 == 0 else 'podcast',
                    source_url=f'https://example.com/content_{i}',
                    title=f'Test Content {i}',
                    status='completed' if i < 3 else 'error'
                )
                session.add(content)
            session.commit()
        
        # Get statistics
        stats = db.get_content_statistics()
        
        print(f"   ✅ Total content: {stats['total_content']}")
        print(f"   ✅ Content by type: {stats['content_by_type']}")
        print(f"   ✅ Content by status: {stats['content_by_status']}")
        print(f"   ✅ Content with errors: {stats['content_with_errors']}")
        print(f"   ✅ Error rate: {stats['error_rate']}%")
        
        # Test database info
        info = db.get_database_info()
        print(f"   ✅ Database size: {info['file_size_mb']} MB")
        
        db.close()
        return True
        
    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

def run_all_tests():
    """Run all model tests"""
    print("🚀 UNIFIED DATABASE MODEL TESTS")
    print("=" * 60)
    
    tests = [
        ("Database Creation", test_database_creation),
        ("ContentItem Operations", test_content_item_operations),
        ("PodcastEpisode Model", test_podcast_episode_model),
        ("ProcessingJob Model", test_processing_jobs),
        ("Analysis & Tags", test_content_analysis_and_tags),
        ("Database Statistics", test_database_statistics)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if success:
                passed += 1
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            print(f"\n🚨 {test_name}: ERROR - {e}")
    
    print(f"\n📊 TEST RESULTS")
    print("=" * 40)
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Unified database models are working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)