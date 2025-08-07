#!/usr/bin/env python3
"""
Quick folder redistribution test with minimal batch
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def quick_folder_test():
    """Test folder redistribution with just 5 newsletters"""
    
    print("⚡ QUICK FOLDER REDISTRIBUTION TEST")
    print("=" * 50)
    
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
    
    # Get private newsletters
    print("\n📧 Getting private newsletters from unread...")
    current_private = get_private_newsletters(client, 'unread')
    print(f"  Found: {len(current_private)} private newsletters")
    
    # Create single test folder
    print("\n📁 Creating test folder...")
    try:
        url = client.BASE_URL + "folders/add"
        params = {'title': 'quick_test'}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            print("  ✅ Created folder: quick_test")
        else:
            print("  ⚠️  Folder may already exist: quick_test")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return
    
    # Move last 5 private newsletters
    print("\n🔀 Moving 5 oldest private newsletters...")
    test_batch = list(current_private.values())[-5:] if len(current_private) >= 5 else list(current_private.values())
    moved_ids = []
    
    for newsletter in test_batch:
        try:
            bookmark_id = newsletter['bookmark_id']
            
            url = client.BASE_URL + "bookmarks/move"
            params = {
                'bookmark_id': bookmark_id,
                'folder': 'quick_test'
            }
            
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                moved_ids.append(bookmark_id)
                print(f"  ✅ Moved: {newsletter['title'][:50]}...")
            else:
                print(f"  ❌ Failed to move (status: {response.status_code})")
            
            time.sleep(1.0)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n📊 Successfully moved: {len(moved_ids)}/5 newsletters")
    
    # Test content access
    print("\n🔍 Testing content access from quick_test folder...")
    folder_private = get_private_newsletters(client, 'quick_test')
    print(f"  Found in folder: {len(folder_private)} private newsletters")
    
    accessible_count = 0
    for bookmark_id, newsletter_data in folder_private.items():
        try:
            text_url = client.BASE_URL + "bookmarks/get_text"
            params = {'bookmark_id': bookmark_id}
            
            response = client.oauth.post(text_url, data=params)
            
            if response.status_code == 200:
                content = response.text
                if len(content.strip()) > 100:
                    accessible_count += 1
                    print(f"    ✅ Accessible: {len(content):,} chars - {newsletter_data['title'][:40]}...")
                else:
                    print(f"    ⚠️  Minimal: {len(content)} chars - {newsletter_data['title'][:40]}...")
            else:
                print(f"    ❌ Not accessible (status: {response.status_code}) - {newsletter_data['title'][:40]}...")
            
            time.sleep(1.5)
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Results
    print(f"\n🎯 RESULTS:")
    print(f"  📧 Newsletters moved: {len(moved_ids)}")
    print(f"  ✅ Content accessible: {accessible_count}")
    success_rate = accessible_count / len(moved_ids) * 100 if moved_ids else 0
    print(f"  📈 Success rate: {success_rate:.1f}%")
    
    # Cleanup
    print(f"\n🔄 Cleaning up...")
    restored = 0
    for bookmark_id in moved_ids:
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
            print(f"    ⚠️  Error restoring: {e}")
    
    print(f"  ✅ Restored: {restored}/{len(moved_ids)} newsletters")
    
    # Strategy assessment
    if accessible_count >= 3:
        print(f"\n🔥 FOLDER STRATEGY SHOWS PROMISE!")
        print(f"  📈 Recommend: Try larger batch (50-100 newsletters)")
        return True
    elif accessible_count >= 1:
        print(f"\n⚡ PARTIAL SUCCESS")
        print(f"  📊 Some benefit, may be worth trying larger batch")
        return True
    else:
        print(f"\n❌ STRATEGY NOT EFFECTIVE")
        print(f"  📊 No additional content access gained")
        return False

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
        print(f"    ❌ Error getting bookmarks: {e}")
    
    return private_bookmarks

if __name__ == '__main__':
    quick_folder_test()