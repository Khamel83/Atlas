#!/usr/bin/env python3
"""
Quick test of private content extraction - just 3 items
"""

import os
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def quick_private_test():
    """Quick test with just a few private items"""
    
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
    
    # Get first few private items from unread
    url = client.BASE_URL + "bookmarks/list"
    params = {'limit': 100, 'folder': 'unread'}
    response = client.oauth.post(url, data=params)
    
    if response.status_code == 200:
        bookmarks = response.json()
        private_items = []
        
        for bookmark in bookmarks[:20]:  # Just check first 20
            if bookmark.get('type') == 'bookmark':
                bookmark_url = bookmark.get('url', '')
                private_source = bookmark.get('private_source', '')
                bookmark_id = bookmark.get('bookmark_id')
                
                is_private = ('instapaper-private' in bookmark_url or 
                            private_source or 
                            bookmark_url.startswith('instapaper://private'))
                
                if is_private and bookmark_id:
                    private_items.append({
                        'id': bookmark_id,
                        'title': bookmark.get('title', 'Untitled')[:50]
                    })
                    
                    if len(private_items) >= 3:  # Just test 3 items
                        break
        
        print(f"📊 Found {len(private_items)} private items to test")
        
        # Test content extraction
        for i, item in enumerate(private_items):
            print(f"\n🔍 Test {i+1}: {item['title']}")
            
            try:
                text_url = client.BASE_URL + "bookmarks/get_text"
                params = {'bookmark_id': item['id']}
                
                response = client.oauth.post(text_url, data=params)
                
                if response.status_code == 200:
                    content = response.text
                    print(f"  ✅ SUCCESS! Content length: {len(content):,} chars")
                    
                    if len(content) > 200:
                        print(f"  Preview: {content[:200]}...")
                    else:
                        print(f"  Content: {content}")
                else:
                    print(f"  ❌ Failed: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        return len(private_items)
    
    else:
        print(f"❌ Failed to get bookmarks: {response.status_code}")
        return 0

if __name__ == '__main__':
    result = quick_private_test()
    print(f"\n🎯 Quick test completed with {result} items")