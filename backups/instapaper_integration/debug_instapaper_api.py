#!/usr/bin/env python3
"""
Debug script to understand Instapaper API response structure
"""

import json
import os
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def debug_api_response():
    """Debug the actual API responses"""
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')  
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful\n")
    
    # Test different folder calls
    folders_to_test = ["unread", "archive", "starred"]
    
    for folder in folders_to_test:
        print(f"🔍 Testing folder: {folder}")
        print("-" * 40)
        
        # Make direct API call to see raw response
        url = client.BASE_URL + "bookmarks/list"
        params = {
            'limit': 10,  # Small limit for debugging
            'folder': folder
        }
        
        try:
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"Response type: {type(data)}")
            print(f"Response length: {len(data) if isinstance(data, list) else 'N/A'}")
            
            if isinstance(data, list) and len(data) > 0:
                print(f"First item type: {type(data[0])}")
                print(f"First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")
                
                # Look for actual bookmarks
                bookmarks = [item for item in data if item.get('type') == 'bookmark']
                meta_items = [item for item in data if item.get('type') != 'bookmark']
                
                print(f"Bookmarks found: {len(bookmarks)}")
                print(f"Meta items: {len(meta_items)}")
                
                if bookmarks:
                    print(f"Sample bookmark structure:")
                    sample = bookmarks[0]
                    for key, value in sample.items():
                        if isinstance(value, str) and len(value) > 50:
                            print(f"  {key}: {value[:50]}...")
                        else:
                            print(f"  {key}: {value}")
                
                print(f"Sample titles:")
                for i, bookmark in enumerate(bookmarks[:3]):
                    title = bookmark.get('title', 'No title')
                    print(f"  {i+1}. {title}")
            
        except Exception as e:
            print(f"❌ Error with {folder}: {e}")
        
        print("\n")
    
    # Also test the high-level method
    print("🔍 Testing client.list_bookmarks() method:")
    print("-" * 40)
    
    try:
        bookmarks = client.list_bookmarks(limit=5, folder="unread")
        print(f"list_bookmarks returned: {len(bookmarks)} items")
        if bookmarks:
            print(f"Sample item: {bookmarks[0] if bookmarks else 'None'}")
    except Exception as e:
        print(f"❌ Error with list_bookmarks: {e}")

if __name__ == '__main__':
    debug_api_response()