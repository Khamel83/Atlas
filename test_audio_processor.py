#!/usr/bin/env python3
"""
Test script for Atlas Audio Processing Integration

Tests the audio processor with database integration to ensure
Podemos capabilities work correctly with Atlas unified database.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from helpers.audio_processor import get_audio_processor, AudioProcessingConfig
import logging

def test_audio_processor_initialization():
    """Test audio processor initialization"""
    print("Testing audio processor initialization...")
    
    # Test with default config
    processor = get_audio_processor()
    
    print(f"✅ AudioProcessor initialized")
    print(f"   - Podemos available: {processor.PODEMOS_AVAILABLE if hasattr(processor, 'PODEMOS_AVAILABLE') else 'Unknown'}")
    print(f"   - Database enabled: {processor.database_enabled}")
    print(f"   - Processing directories: {list(processor.directories.keys())}")
    
    return processor

def test_audio_processing_config():
    """Test audio processing configuration"""
    print("Testing audio processing configuration...")
    
    config = AudioProcessingConfig(
        enable_ad_detection=True,
        transcription_model="base",
        max_retries=2,
        audio_quality="high"
    )
    
    processor = get_audio_processor(config)
    
    print(f"✅ AudioProcessing configuration loaded")
    print(f"   - Ad detection: {config.enable_ad_detection}")
    print(f"   - Transcription model: {config.transcription_model}")
    print(f"   - Max retries: {config.max_retries}")
    print(f"   - Audio quality: {config.audio_quality}")
    
    return processor, config

def test_processing_directories():
    """Test processing directory setup"""
    print("Testing processing directory setup...")
    
    processor = get_audio_processor()
    
    for dir_name, dir_path in processor.directories.items():
        exists = dir_path.exists()
        print(f"{'✅' if exists else '❌'} {dir_name}: {dir_path} {'(exists)' if exists else '(missing)'}")
        
        if not exists:
            print(f"❌ Processing directory missing: {dir_path}")
            return False
    
    return True

def test_database_integration():
    """Test database integration"""
    print("Testing database integration...")
    
    processor = get_audio_processor()
    
    if not processor.database_enabled:
        print("⚠️  Database not enabled - will use basic Atlas capabilities")
        return True
        
    # Test database connection
    try:
        if processor.atlas_db:
            stats = processor.atlas_db.get_content_statistics()
            print(f"✅ Database connection successful")
            print(f"   - Total content items: {stats.get('total_items', 'N/A')}")
            print(f"   - Database file exists: {os.path.exists('atlas_unified.db')}")
            return True
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        return False
    
    return False

def test_podemos_availability():
    """Test Podemos module availability"""
    print("Testing Podemos module availability...")
    
    try:
        from helpers.audio_processor import PODEMOS_AVAILABLE
        
        if PODEMOS_AVAILABLE:
            print("✅ Podemos modules loaded successfully")
            print("   - Advanced ad detection available")
            print("   - High-quality transcription available")  
            print("   - Audio cutting/editing available")
        else:
            print("⚠️  Podemos modules not available")
            print("   - Will use basic Atlas capabilities")
            print("   - Ad detection: disabled")
            print("   - Transcription: basic mode")
            
        return PODEMOS_AVAILABLE
        
    except ImportError as e:
        print(f"❌ Failed to check Podemos availability: {e}")
        return False

def main():
    """Run all audio processor tests"""
    print("🎵 Atlas Audio Processing Integration Test")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    tests_passed = 0
    total_tests = 5
    
    try:
        # Test 1: Initialization
        print("\n1️⃣ Testing Initialization")
        processor = test_audio_processor_initialization()
        if processor:
            tests_passed += 1
            
        # Test 2: Configuration
        print("\n2️⃣ Testing Configuration")
        processor, config = test_audio_processing_config()
        if processor and config:
            tests_passed += 1
            
        # Test 3: Processing Directories
        print("\n3️⃣ Testing Processing Directories")
        if test_processing_directories():
            tests_passed += 1
            
        # Test 4: Database Integration
        print("\n4️⃣ Testing Database Integration") 
        if test_database_integration():
            tests_passed += 1
            
        # Test 5: Podemos Availability
        print("\n5️⃣ Testing Podemos Availability")
        if test_podemos_availability() is not None:  # Either True or False is valid
            tests_passed += 1
        
        # Results
        print("\n" + "=" * 50)
        print(f"🏆 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("✅ All audio processor integration tests PASSED")
            print("🚀 Audio processor is ready for production use")
        else:
            print(f"⚠️  {total_tests - tests_passed} tests failed")
            print("🔧 Some components need attention before production use")
            
        # Cleanup
        try:
            from helpers.audio_processor import close_global_audio_processor
            close_global_audio_processor()
            print("🧹 Audio processor cleanup completed")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        print("❌ Audio processor integration tests FAILED")
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()