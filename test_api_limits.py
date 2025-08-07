#!/usr/bin/env python3
"""
Test API limits and explore for additional private content
"""

import os
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def test_api_limits():
    """Test different API approaches to find more private content"""
    
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
    print("🔍 Testing API limits and additional private content access...")
    
    # Test different folders
    folders = ['unread', 'archive', 'starred']
    total_private_found = 0
    private_by_folder = {}
    
    for folder in folders:
        print(f"\n📁 Testing folder: {folder}")
        try:
            url = client.BASE_URL + "bookmarks/list"
            params = {'limit': 500, 'folder': folder}
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                bookmarks = response.json()
                private_count = 0
                
                for bookmark in bookmarks:
                    if bookmark.get('type') == 'bookmark':
                        bookmark_url = bookmark.get('url', '')
                        private_source = bookmark.get('private_source', '')
                        
                        is_private = ('instapaper-private' in bookmark_url or 
                                    private_source or 
                                    bookmark_url.startswith('instapaper://private'))
                        
                        if is_private:
                            private_count += 1
                
                print(f"  Private newsletters found: {private_count}")
                private_by_folder[folder] = private_count
                total_private_found += private_count
                
            else:
                print(f"  ❌ API failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total unique private content accessible via API: {total_private_found}")
    for folder, count in private_by_folder.items():
        print(f"    {folder}: {count} private items")
    
    # Test pagination with have parameter
    print(f"\n🔄 Testing pagination...")
    try:
        url = client.BASE_URL + "bookmarks/list" 
        params = {'limit': 500, 'folder': 'unread'}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            bookmarks = response.json()
            if bookmarks:
                last_bookmark_id = bookmarks[-1].get('bookmark_id')
                print(f"  Last bookmark ID in first batch: {last_bookmark_id}")
                
                # Try to get next batch
                params_next = {'limit': 500, 'folder': 'unread', 'have': last_bookmark_id}
                response_next = client.oauth.post(url, data=params_next)
                
                if response_next.status_code == 200:
                    next_bookmarks = response_next.json()
                    print(f"  Next batch contains: {len(next_bookmarks)} items")
                    
                    # Count private in next batch
                    private_in_next = 0
                    for bookmark in next_bookmarks:
                        if bookmark.get('type') == 'bookmark':
                            bookmark_url = bookmark.get('url', '')
                            private_source = bookmark.get('private_source', '')
                            
                            is_private = ('instapaper-private' in bookmark_url or 
                                        private_source or 
                                        bookmark_url.startswith('instapaper://private'))
                            
                            if is_private:
                                private_in_next += 1
                    
                    print(f"  Private newsletters in next batch: {private_in_next}")
                    
                else:
                    print(f"  ❌ Next batch failed: {response_next.status_code}")
    
    except Exception as e:
        print(f"  ❌ Pagination test error: {e}")

if __name__ == '__main__':
    test_api_limits()