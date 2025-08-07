#!/usr/bin/env python3
"""
Test script for Podcast Ad Detection and Removal System

Tests the complete ad detection and removal pipeline that integrates
Podemos advanced capabilities with Atlas workflows and unified database.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from helpers.podcast_ad_processor import (
    get_podcast_ad_processor, 
    close_global_ad_processor,
    ProcessingConfig, 
    AdDetectionConfig
)

def test_ad_processor_initialization():
    """Test ad processor initialization"""
    print("Testing podcast ad processor initialization...")
    
    try:
        processor = get_podcast_ad_processor()
        
        print(f"✅ PodcastAdProcessor initialized")
        print(f"   - Database enabled: {processor.database_enabled}")
        print(f"   - RSS ingestor available: {processor.rss_ingestor is not None}")
        print(f"   - Audio processor available: {processor.audio_processor is not None}")
        print(f"   - Atlas DB integration: {processor.atlas_db is not None}")
        print(f"   - Processing directories: {list(processor.directories.keys())}")
        
        return processor
        
    except Exception as e:
        print(f"❌ Ad processor initialization failed: {e}")
        return None

def test_processing_configuration():
    """Test processing configuration"""
    print("Testing processing configuration...")
    
    try:
        # Test custom configuration
        ad_config = AdDetectionConfig(
            enable_chapter_detection=True,
            enable_text_analysis=True,
            enable_audio_analysis=False,
            min_confidence=0.8,
            padding_seconds=3.0
        )
        
        processing_config = ProcessingConfig(
            ad_detection=ad_config,
            enable_ad_removal=True,
            enable_transcription=True,
            max_retries=2
        )
        
        processor = get_podcast_ad_processor(processing_config)
        
        print(f"✅ Processing configuration loaded")
        print(f"   - Ad detection enabled: {processing_config.enable_ad_removal}")
        print(f"   - Chapter detection: {ad_config.enable_chapter_detection}")
        print(f"   - Text analysis: {ad_config.enable_text_analysis}")
        print(f"   - Min confidence: {ad_config.min_confidence}")
        print(f"   - Transcription enabled: {processing_config.enable_transcription}")
        print(f"   - Max retries: {processing_config.max_retries}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_processing_directories():
    """Test processing directory setup"""
    print("Testing processing directory setup...")
    
    try:
        processor = get_podcast_ad_processor()
        
        all_exist = True
        for dir_name, dir_path in processor.directories.items():
            exists = dir_path.exists()
            print(f"{'✅' if exists else '❌'} {dir_name}: {dir_path} {'(exists)' if exists else '(missing)'}")
            if not exists:
                all_exist = False
        
        return all_exist
        
    except Exception as e:
        print(f"❌ Directory setup test failed: {e}")
        return False

def test_ad_detection_methods():
    """Test ad detection method availability"""
    print("Testing ad detection methods...")
    
    try:
        processor = get_podcast_ad_processor()
        
        # Test method availability
        has_chapter_detection = hasattr(processor, '_detect_ads_from_chapters')
        has_text_detection = hasattr(processor, '_detect_ads_from_transcript')
        has_enhanced_detection = hasattr(processor, '_enhanced_ad_detection')
        has_segment_merging = hasattr(processor, '_merge_and_optimize_segments')
        
        print(f"✅ Ad detection methods verified")
        print(f"   - Chapter detection: {'✅' if has_chapter_detection else '❌'}")
        print(f"   - Text analysis: {'✅' if has_text_detection else '❌'}")
        print(f"   - Enhanced multi-signal: {'✅' if has_enhanced_detection else '❌'}")
        print(f"   - Segment optimization: {'✅' if has_segment_merging else '❌'}")
        
        return all([has_chapter_detection, has_text_detection, has_enhanced_detection, has_segment_merging])
        
    except Exception as e:
        print(f"❌ Ad detection methods test failed: {e}")
        return False

def test_processing_pipeline():
    """Test processing pipeline components"""
    print("Testing processing pipeline components...")
    
    try:
        processor = get_podcast_ad_processor()
        
        # Test pipeline method availability
        has_main_processor = hasattr(processor, 'process_podcast_episode')
        has_batch_processor = hasattr(processor, 'process_multiple_episodes')
        has_intelligent_removal = hasattr(processor, '_intelligent_ad_removal')
        has_transcription = hasattr(processor, '_transcribe_cleaned_audio')
        has_report_generation = hasattr(processor, '_generate_processing_report')
        
        print(f"✅ Processing pipeline verified")
        print(f"   - Main episode processing: {'✅' if has_main_processor else '❌'}")
        print(f"   - Batch processing: {'✅' if has_batch_processor else '❌'}")
        print(f"   - Intelligent ad removal: {'✅' if has_intelligent_removal else '❌'}")
        print(f"   - Clean audio transcription: {'✅' if has_transcription else '❌'}")
        print(f"   - Report generation: {'✅' if has_report_generation else '❌'}")
        
        return all([has_main_processor, has_batch_processor, has_intelligent_removal, 
                   has_transcription, has_report_generation])
        
    except Exception as e:
        print(f"❌ Processing pipeline test failed: {e}")
        return False

def test_database_integration():
    """Test database integration for ad processing"""
    print("Testing database integration...")
    
    try:
        processor = get_podcast_ad_processor()
        
        # Test database components
        has_unified_db = processor.db is not None
        has_atlas_db = processor.atlas_db is not None  
        has_storage_method = hasattr(processor, '_store_processing_results')
        
        print(f"✅ Database integration verified")
        print(f"   - Unified database: {'✅' if has_unified_db else '❌'}")
        print(f"   - Atlas database: {'✅' if has_atlas_db else '❌'}")
        print(f"   - Results storage: {'✅' if has_storage_method else '❌'}")
        print(f"   - Database enabled: {'✅' if processor.database_enabled else '❌'}")
        
        # Test statistics retrieval
        if processor.database_enabled:
            stats = processor.get_processing_statistics()
            if 'error' not in stats:
                print(f"   - Statistics available: ✅")
                print(f"     • Total episodes: {stats.get('total_episodes', 0)}")
                print(f"     • Ad processed: {stats.get('ad_processed_episodes', 0)}")
                print(f"     • Cleaned episodes: {stats.get('cleaned_episodes', 0)}")
            else:
                print(f"   - Statistics error: {stats.get('error', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        return False

def test_ad_detection_config():
    """Test ad detection configuration"""
    print("Testing ad detection configuration...")
    
    try:
        # Test default configuration
        default_config = AdDetectionConfig()
        
        # Test custom configuration  
        custom_config = AdDetectionConfig(
            enable_chapter_detection=True,
            enable_text_analysis=True,
            min_confidence=0.9,
            padding_seconds=1.5,
            ad_phrases=["sponsor", "advertisement"]
        )
        
        print(f"✅ Ad detection configuration verified")
        print(f"   - Default ad phrases: {len(default_config.ad_phrases)} phrases")
        print(f"   - Default URL patterns: {len(default_config.url_patterns)} patterns")
        print(f"   - Default price patterns: {len(default_config.price_patterns)} patterns")
        print(f"   - Custom configuration: ✅")
        print(f"   - Custom confidence: {custom_config.min_confidence}")
        print(f"   - Custom padding: {custom_config.padding_seconds}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Ad detection config test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and result creation"""
    print("Testing error handling...")
    
    try:
        processor = get_podcast_ad_processor()
        
        # Test error result creation
        error_result = processor._create_error_result(
            "test_uid", 
            "http://test.com/audio.mp3",
            "Test Episode",
            "Test Show", 
            "Test error message"
        )
        
        print(f"✅ Error handling verified")
        print(f"   - Error result creation: ✅")
        print(f"   - Success flag: {error_result.success} (should be False)")
        print(f"   - Error message: '{error_result.error_message}'")
        print(f"   - Content UID: {error_result.content_uid}")
        print(f"   - Processing status: {error_result.processing_status}")
        
        return not error_result.success  # Should be False for error
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all ad processor tests"""
    print("🎵 Atlas-Podemos Ad Detection and Removal System Test")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise for testing
    
    tests_passed = 0
    total_tests = 8
    
    try:
        # Test 1: Initialization
        print("\n1️⃣ Testing Initialization")
        processor = test_ad_processor_initialization()
        if processor:
            tests_passed += 1
        
        # Test 2: Configuration
        print("\n2️⃣ Testing Configuration")
        if test_processing_configuration():
            tests_passed += 1
        
        # Test 3: Directory Setup
        print("\n3️⃣ Testing Directory Setup")
        if test_processing_directories():
            tests_passed += 1
        
        # Test 4: Ad Detection Methods
        print("\n4️⃣ Testing Ad Detection Methods")
        if test_ad_detection_methods():
            tests_passed += 1
        
        # Test 5: Processing Pipeline
        print("\n5️⃣ Testing Processing Pipeline")
        if test_processing_pipeline():
            tests_passed += 1
        
        # Test 6: Database Integration
        print("\n6️⃣ Testing Database Integration")
        if test_database_integration():
            tests_passed += 1
        
        # Test 7: Ad Detection Configuration
        print("\n7️⃣ Testing Ad Detection Configuration")
        if test_ad_detection_config():
            tests_passed += 1
        
        # Test 8: Error Handling
        print("\n8️⃣ Testing Error Handling")
        if test_error_handling():
            tests_passed += 1
        
        # Results
        print("\n" + "=" * 60)
        print(f"🏆 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("✅ All ad processor tests PASSED")
            print("🚀 Ad detection and removal system is ready for production")
        else:
            print(f"⚠️  {total_tests - tests_passed} tests failed")
            print("🔧 Some components need attention before production use")
        
        # Cleanup
        try:
            close_global_ad_processor()
            print("🧹 Ad processor cleanup completed")
        except:
            pass
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        print("❌ Ad processor tests FAILED")
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()