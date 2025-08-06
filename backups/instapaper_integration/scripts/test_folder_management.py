#!/usr/bin/env python3
"""
Test Instapaper folder management capabilities to see if reorganizing 
bookmarks could help overcome the 500-bookmark limit per folder.
"""

import os
import json
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def test_folder_capabilities():
    """Test what folder management options are available"""
    
    load_dotenv()
    
    # Load credentials
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing Instapaper credentials in .env file")
        return
    
    print("🔍 TESTING INSTAPAPER FOLDER MANAGEMENT CAPABILITIES")
    print("=" * 60)
    
    # Initialize client
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    # Authenticate
    print("🔐 Authenticating...")
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print()
    
    # Test 1: Get user account info
    print("📊 STEP 1: Account Information")
    print("-" * 40)
    
    try:
        url = client.BASE_URL + "account/verify_credentials"
        response = client.oauth.post(url)
        
        if response.status_code == 200:
            account_info = response.json()
            print(f"  Username: {account_info[0].get('username', 'N/A')}")
            print(f"  User ID: {account_info[0].get('user_id', 'N/A')}")
            print(f"  Subscription active: {account_info[0].get('subscription_is_active', 'N/A')}")
            print(f"  Type: {account_info[0].get('type', 'N/A')}")
        else:
            print(f"  ❌ Failed to get account info: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error getting account info: {e}")
    
    print()
    
    # Test 2: List folders
    print("📁 STEP 2: Available Folders")
    print("-" * 40)
    
    try:
        url = client.BASE_URL + "folders/list"
        response = client.oauth.post(url)
        
        if response.status_code == 200:
            folders_data = response.json()
            print(f"  Found {len(folders_data)} folders:")
            
            for folder in folders_data:
                folder_id = folder.get('folder_id')
                title = folder.get('title', 'Untitled')
                display_title = folder.get('display_title', title)
                position = folder.get('position', 'N/A')
                
                print(f"    ID: {folder_id:6} | '{display_title}' (pos: {position})")
        else:
            print(f"  ❌ Failed to list folders: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error listing folders: {e}")
    
    print()
    
    # Test 3: Try to create a new folder (to test if this is possible)
    print("🆕 STEP 3: Test Folder Creation")
    print("-" * 40)
    
    try:
        url = client.BASE_URL + "folders/add"
        test_folder_name = "API_Test_Folder_2025"
        
        params = {'title': test_folder_name}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            folder_info = response.json()
            print(f"  ✅ Successfully created folder: '{test_folder_name}'")
            print(f"  Folder ID: {folder_info[0].get('folder_id')}")
            
            # Clean up - try to delete the test folder
            folder_id = folder_info[0].get('folder_id')
            delete_url = client.BASE_URL + "folders/delete"
            delete_params = {'folder_id': folder_id}
            delete_response = client.oauth.post(delete_url, data=delete_params)
            
            if delete_response.status_code == 200:
                print(f"  🗑️  Successfully deleted test folder")
            else:
                print(f"  ⚠️  Created test folder but couldn't delete it (ID: {folder_id})")
                
        else:
            print(f"  ❌ Failed to create folder: {response.status_code}")
            print(f"  Response: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Error testing folder creation: {e}")
    
    print()
    
    # Test 4: Test bookmark moving between folders
    print("🔄 STEP 4: Test Bookmark Moving")
    print("-" * 40)
    
    try:
        # First, get a bookmark from unread folder
        bookmarks = client.list_bookmarks(limit=1, folder="unread")
        
        if not bookmarks:
            print("  ❌ No bookmarks found in unread folder to test with")
        else:
            bookmark = bookmarks[0]
            bookmark_id = bookmark.get('bookmark_id')
            title = bookmark.get('title', 'Untitled')[:50]
            
            print(f"  Testing with bookmark: '{title}' (ID: {bookmark_id})")
            
            # Try to move to archive folder
            url = client.BASE_URL + "bookmarks/archive"
            params = {'bookmark_id': bookmark_id}
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                print("  ✅ Successfully moved bookmark to archive")
                
                # Move it back to unread
                unarchive_url = client.BASE_URL + "bookmarks/unarchive"
                unarchive_response = client.oauth.post(unarchive_url, data=params)
                
                if unarchive_response.status_code == 200:
                    print("  ✅ Successfully moved bookmark back to unread")
                else:
                    print(f"  ⚠️  Moved to archive but couldn't move back: {unarchive_response.status_code}")
            else:
                print(f"  ❌ Failed to move bookmark: {response.status_code}")
                print(f"  Response: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Error testing bookmark moving: {e}")
    
    print()
    
    # Test 5: Check pagination parameters more thoroughly
    print("🔍 STEP 5: Advanced Pagination Testing")
    print("-" * 40)
    
    try:
        # Test different pagination approaches
        folder = "archive"  # Use archive since it's likely to have many items
        
        print(f"  Testing pagination in '{folder}' folder...")
        
        # First request - get initial 500
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': folder}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            initial_bookmarks = response.json()
            print(f"  Initial request: {len(initial_bookmarks)} bookmarks")
            
            if len(initial_bookmarks) == 500:
                # Try to get more using 'have' parameter
                bookmark_ids = [str(b.get('bookmark_id')) for b in initial_bookmarks if b.get('bookmark_id')]
                have_param = ','.join(bookmark_ids)
                
                params_with_have = {
                    'limit': 500,
                    'folder': folder,
                    'have': have_param
                }
                
                response2 = client.oauth.post(url, data=params_with_have)
                
                if response2.status_code == 200:
                    next_bookmarks = response2.json()
                    print(f"  Second request (with 'have'): {len(next_bookmarks)} bookmarks")
                    
                    if len(next_bookmarks) > 0:
                        print("  ✅ Pagination appears to work!")
                        # Check if we got different bookmarks
                        next_ids = set(str(b.get('bookmark_id')) for b in next_bookmarks if b.get('bookmark_id'))
                        initial_ids = set(str(b.get('bookmark_id')) for b in initial_bookmarks if b.get('bookmark_id'))
                        
                        overlap = initial_ids & next_ids
                        print(f"  Overlap between requests: {len(overlap)} bookmarks")
                        
                        if len(overlap) == 0:
                            print("  ✅ No overlap - we got different bookmarks!")
                        else:
                            print("  ⚠️  Some overlap detected")
                    else:
                        print("  ❌ No additional bookmarks returned with 'have' parameter")
                else:
                    print(f"  ❌ Second request failed: {response2.status_code}")
            else:
                print(f"  📊 Folder has {len(initial_bookmarks)} bookmarks (less than 500)")
        else:
            print(f"  ❌ Initial request failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Error testing advanced pagination: {e}")
    
    print()
    
    # Summary
    print("🎯 SUMMARY & RECOMMENDATIONS")
    print("=" * 60)
    
    print("Based on the API testing:")
    print("1. Account status affects API access limits")
    print("2. Folder creation/deletion may be possible")
    print("3. Bookmark moving between folders is supported")
    print("4. The 'have' parameter is the key to pagination")
    print()
    print("💡 POTENTIAL WORKAROUND:")
    print("If the API allows folder creation and bookmark moving,")
    print("you could potentially:")
    print("1. Create multiple new folders")
    print("2. Move bookmarks from large folders into smaller ones")
    print("3. Extract from each folder (staying under 500 limit)")
    print("4. Combine the results")
    print()
    print("⚠️  However, this would be a complex process and")
    print("might violate Instapaper's terms of service.")

if __name__ == '__main__':
    test_folder_capabilities()