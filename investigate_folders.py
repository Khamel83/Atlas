#!/usr/bin/env python3
"""
Investigate actual Instapaper folders and get comprehensive data
"""

import json
import os
from time import sleep
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def investigate_instapaper_structure():
    """Get the actual folder structure and test each folder"""
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')  
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print("=" * 60)
    
    # Step 1: Get folder list
    print("📁 STEP 1: Getting folder list...")
    folders = get_folder_list(client)
    
    # Step 2: Test each folder individually  
    print("\n📊 STEP 2: Testing each folder...")
    test_folder_access(client, folders)
    
    # Step 3: Try alternative approaches
    print("\n🔍 STEP 3: Testing alternative parameters...")
    test_alternative_approaches(client)

def get_folder_list(client):
    """Get the actual folder list from the API"""
    
    url = client.BASE_URL + "folders/list"
    
    try:
        response = client.oauth.post(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"Folders response type: {type(data)}")
        
        if isinstance(data, list):
            print(f"Found {len(data)} folder items:")
            
            folders = []
            for item in data:
                if isinstance(item, dict):
                    print(f"  - {item}")
                    if item.get('type') == 'folder':
                        folders.append(item)
            
            print(f"\nActual folders: {len(folders)}")
            for folder in folders:
                folder_id = folder.get('folder_id')
                title = folder.get('title', 'No title')
                print(f"  ID: {folder_id}, Title: '{title}'")
            
            return folders
        else:
            print(f"Unexpected folder response: {data}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting folders: {e}")
        return []

def test_folder_access(client, folders):
    """Test accessing each folder individually"""
    
    # Test default folders first
    default_folders = ["unread", "archive", "starred"]
    
    print("Testing default folder names:")
    for folder_name in default_folders:
        count = test_single_folder(client, folder_name, is_name=True)
        print(f"  {folder_name}: {count} bookmarks")
    
    # Test actual folder IDs
    if folders:
        print("\nTesting actual folder IDs:")
        for folder in folders:
            folder_id = folder.get('folder_id')
            title = folder.get('title', f'ID_{folder_id}')
            
            if folder_id:
                count = test_single_folder(client, str(folder_id), is_name=False)
                print(f"  {title} (ID: {folder_id}): {count} bookmarks")

def test_single_folder(client, folder_identifier, is_name=True):
    """Test a single folder and return bookmark count"""
    
    url = client.BASE_URL + "bookmarks/list"
    
    if is_name:
        params = {'limit': 500, 'folder': folder_identifier}
    else:
        params = {'limit': 500, 'folder_id': folder_identifier}
    
    try:
        response = client.oauth.post(url, data=params)
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, list):
            bookmarks = [item for item in data if item.get('type') == 'bookmark']
            return len(bookmarks)
        else:
            return 0
            
    except Exception as e:
        print(f"    Error testing {folder_identifier}: {e}")
        return 0

def test_alternative_approaches(client):
    """Test alternative API parameters"""
    
    print("Testing without folder parameter (all bookmarks):")
    
    url = client.BASE_URL + "bookmarks/list"
    
    approaches = [
        {'limit': 500},  # No folder
        {'limit': 500, 'folder': ''},  # Empty folder
        {'limit': 500, 'folder': 'all'},  # Try 'all'
    ]
    
    for i, params in enumerate(approaches):
        try:
            print(f"  Approach {i+1}: {params}")
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                bookmarks = [item for item in data if item.get('type') == 'bookmark']
                print(f"    Result: {len(bookmarks)} bookmarks")
                
                # Show sample titles
                if bookmarks:
                    print(f"    Sample titles:")
                    for j, bookmark in enumerate(bookmarks[:3]):
                        title = bookmark.get('title', 'No title')[:50]
                        print(f"      {j+1}. {title}")
            else:
                print(f"    Unexpected response: {type(data)}")
                
        except Exception as e:
            print(f"    Error: {e}")
        
        sleep(1)

if __name__ == '__main__':
    print("🔍 INVESTIGATING INSTAPAPER FOLDER STRUCTURE")
    print("🎯 Goal: Find all your folders and get complete bookmark count")
    print()
    
    investigate_instapaper_structure()