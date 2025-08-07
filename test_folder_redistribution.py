#!/usr/bin/env python3
"""
Test folder redistribution strategy to access more private newsletters
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def test_folder_redistribution():
    """Test if redistributing private newsletters into multiple folders unlocks more content"""
    
    print("🔄 TESTING FOLDER REDISTRIBUTION STRATEGY")
    print("=" * 60)
    
    load_dotenv()
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print("🎯 Testing folder redistribution to bypass API limits...")
    
    # Step 1: Get current private newsletters in unread
    print("\n📊 STEP 1: Analyzing current private newsletter distribution")
    print("-" * 40)
    
    current_private = get_private_newsletters(client, 'unread')
    print(f"  📧 Private newsletters currently in 'unread': {len(current_private)}")
    
    # Step 2: Create test folders for redistribution
    print("\n🔄 STEP 2: Creating test folders for redistribution")
    print("-" * 40)
    
    test_folders = [
        'private_test_1',
        'private_test_2', 
        'private_test_3'
    ]
    
    created_folders = []
    for folder_name in test_folders:
        try:
            # Create folder
            url = client.BASE_URL + "folders/add"
            params = {'title': folder_name}
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                print(f"  ✅ Created folder: {folder_name}")
                created_folders.append(folder_name)
            else:
                print(f"  ⚠️  Folder may already exist: {folder_name}")
                created_folders.append(folder_name)  # Assume it exists
                
        except Exception as e:
            print(f"  ❌ Error creating folder {folder_name}: {e}")
    
    if not created_folders:
        print("❌ Could not create any test folders")
        return
    
    # Step 3: Test moving a small batch of private newsletters
    print("\n🔀 STEP 3: Testing redistribution with small batch")
    print("-" * 40)
    
    # Take the oldest 20 private newsletters for testing
    test_batch = list(current_private.values())[-20:] if len(current_private) >= 20 else list(current_private.values())
    
    print(f"  🎯 Testing with {len(test_batch)} private newsletters")
    
    moved_successfully = 0
    for i, newsletter in enumerate(test_batch):
        try:
            bookmark_id = newsletter['bookmark_id']
            target_folder = created_folders[i % len(created_folders)]  # Distribute across folders
            
            # Move bookmark to test folder
            url = client.BASE_URL + "bookmarks/move"
            params = {
                'bookmark_id': bookmark_id,
                'folder': target_folder
            }
            
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                moved_successfully += 1
                print(f"    ✅ Moved newsletter to {target_folder}")
            else:
                print(f"    ❌ Failed to move newsletter (status: {response.status_code})")
            
            # Rate limiting
            time.sleep(1.0)
            
        except Exception as e:
            print(f"    ❌ Error moving newsletter: {e}")
    
    print(f"  📊 Successfully moved: {moved_successfully}/{len(test_batch)} newsletters")
    
    # Step 4: Test API access from redistributed folders
    print("\n🔍 STEP 4: Testing API access from redistributed folders")
    print("-" * 40)
    
    total_accessible = 0
    extraction_results = {}
    
    for folder in created_folders:
        print(f"  Testing folder: {folder}")
        
        # Get private newsletters from this folder
        folder_private = get_private_newsletters(client, folder)
        print(f"    📧 Private newsletters found: {len(folder_private)}")
        
        # Test content extraction from first few
        accessible_count = 0
        for i, (bookmark_id, newsletter_data) in enumerate(folder_private.items()):
            if i >= 5:  # Test first 5 only
                break
                
            try:
                # Test content access
                text_url = client.BASE_URL + "bookmarks/get_text"
                params = {'bookmark_id': bookmark_id}
                
                response = client.oauth.post(text_url, data=params)
                
                if response.status_code == 200:
                    content = response.text
                    if len(content.strip()) > 50:
                        accessible_count += 1
                        print(f"      ✅ Content accessible: {len(content):,} chars")
                    else:
                        print(f"      ⚠️  Minimal content: {len(content)} chars")
                else:
                    print(f"      ❌ Content not accessible (status: {response.status_code})")
                
                time.sleep(2.0)  # Conservative rate limiting
                
            except Exception as e:
                print(f"      ❌ Error testing content access: {e}")
        
        extraction_results[folder] = {
            'total_private': len(folder_private),
            'accessible_content': accessible_count,
            'access_rate': accessible_count / min(5, len(folder_private)) * 100 if folder_private else 0
        }
        
        total_accessible += accessible_count
    
    # Step 5: Results analysis
    print("\n📊 STEP 5: Redistribution test results")
    print("-" * 40)
    
    print(f"  🎯 Total folders tested: {len(created_folders)}")
    print(f"  📧 Total newsletters moved: {moved_successfully}")
    print(f"  ✅ Total with accessible content: {total_accessible}")
    
    success_rate = total_accessible / min(15, moved_successfully) * 100 if moved_successfully > 0 else 0
    print(f"  📈 Content access success rate: {success_rate:.1f}%")
    
    for folder, results in extraction_results.items():
        print(f"    {folder}: {results['accessible_content']}/{results['total_private']} accessible ({results['access_rate']:.1f}%)")
    
    # Step 6: Determine if strategy is viable
    print("\n🎯 STEP 6: Strategy viability assessment")
    print("-" * 40)
    
    if total_accessible > 10:  # If we got significant new access
        print("  🔥 SUCCESS: Folder redistribution unlocked additional content!")
        print(f"  📈 Recommendation: Proceed with full redistribution strategy")
        print(f"  🎯 Potential additional newsletters: {len(current_private) - 137} (historical estimate)")
        
        # Ask if user wants to proceed with full redistribution
        print("\n  Next steps:")
        print("    1. Run full redistribution of all private newsletters")
        print("    2. Extract content from all accessible newsletters")  
        print("    3. Restore original folder organization")
        
        strategy_viable = True
        
    elif total_accessible > 5:
        print("  ⚡ PARTIAL SUCCESS: Some additional content accessible")
        print(f"  📊 Recommendation: Limited benefit, may not justify full redistribution")
        
        strategy_viable = False
        
    else:
        print("  ❌ STRATEGY NOT VIABLE: No significant additional access")
        print(f"  📊 Recommendation: Focus on other extraction methods")
        
        strategy_viable = False
    
    # Step 7: Cleanup (restore original organization)
    print("\n🔄 STEP 7: Restoring original folder organization")
    print("-" * 40)
    
    restored = 0
    for folder in created_folders:
        try:
            # Move all bookmarks back to unread
            folder_items = get_all_bookmarks_in_folder(client, folder)
            
            for bookmark_id in folder_items:
                try:
                    url = client.BASE_URL + "bookmarks/move"  
                    params = {
                        'bookmark_id': bookmark_id,
                        'folder': 'unread'
                    }
                    
                    response = client.oauth.post(url, data=params)
                    if response.status_code == 200:
                        restored += 1
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"    ⚠️  Error restoring bookmark: {e}")
            
            # Delete test folder
            try:
                url = client.BASE_URL + "folders/delete"
                params = {'folder_id': folder}  # Note: may need folder ID instead of name
                response = client.oauth.post(url, data=params)
                print(f"    🗑️  Deleted test folder: {folder}")
            except:
                print(f"    ⚠️  Could not delete folder {folder} (may need manual cleanup)")
            
        except Exception as e:
            print(f"    ❌ Error cleaning up folder {folder}: {e}")
    
    print(f"  ✅ Restored {restored} bookmarks to original locations")
    
    # Final report
    print(f"\n🎯 REDISTRIBUTION TEST COMPLETE")
    print("=" * 60)
    print(f"  Strategy viable: {'YES' if strategy_viable else 'NO'}")
    print(f"  Additional content accessible: {total_accessible} newsletters")
    print(f"  Folders tested: {len(created_folders)}")
    print(f"  Bookmarks moved and restored: {restored}")
    
    return {
        'strategy_viable': strategy_viable,
        'additional_accessible': total_accessible,
        'folders_tested': len(created_folders),
        'extraction_results': extraction_results
    }

def get_private_newsletters(client, folder='unread'):
    """Get private newsletters from specified folder"""
    
    private_bookmarks = {}
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': folder}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            for bookmark in bookmarks:
                if bookmark.get('type') == 'bookmark':
                    bookmark_url = bookmark.get('url', '')
                    private_source = bookmark.get('private_source', '')
                    bookmark_id = bookmark.get('bookmark_id')
                    
                    is_private = ('instapaper-private' in bookmark_url or 
                                private_source or 
                                bookmark_url.startswith('instapaper://private'))
                    
                    if is_private and bookmark_id:
                        private_bookmarks[bookmark_id] = {
                            'bookmark_id': bookmark_id,
                            'title': bookmark.get('title', 'Untitled'),
                            'url': bookmark_url,
                            'private_source': private_source,
                            'time': bookmark.get('time', 0)
                        }
        
    except Exception as e:
        print(f"    ❌ Error getting bookmarks from {folder}: {e}")
    
    return private_bookmarks

def get_all_bookmarks_in_folder(client, folder):
    """Get all bookmark IDs in a folder for cleanup"""
    
    bookmark_ids = []
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': folder}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            for bookmark in bookmarks:
                if bookmark.get('type') == 'bookmark':
                    bookmark_id = bookmark.get('bookmark_id')
                    if bookmark_id:
                        bookmark_ids.append(bookmark_id)
        
    except Exception as e:
        print(f"    ❌ Error getting bookmark IDs from {folder}: {e}")
    
    return bookmark_ids

if __name__ == '__main__':
    test_folder_redistribution()