#!/usr/bin/env python3
"""
Aggressive private newsletter extraction using multiple strategies
Based on deep API research findings
"""

import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def aggressive_private_extraction():
    """Try multiple strategies to extract maximum private newsletters"""
    
    print("🔥 AGGRESSIVE PRIVATE NEWSLETTER EXTRACTION")
    print("=" * 70)
    
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
    
    strategies = [
        ("folder_all_approach", test_all_folder_access),
        ("archive_folder_test", test_archive_folder),
        ("starred_folder_test", test_starred_folder), 
        ("pagination_variants", test_pagination_variants),
        ("batch_id_access", test_batch_bookmark_access),
        ("private_url_patterns", test_private_url_patterns)
    ]
    
    results = {}
    
    for strategy_name, strategy_func in strategies:
        print(f"\n🧪 STRATEGY: {strategy_name.upper()}")
        print("-" * 50)
        
        try:
            strategy_result = strategy_func(client)
            results[strategy_name] = strategy_result
            
            print(f"  📊 Result: {strategy_result}")
            
            # Rate limiting between strategies
            time.sleep(3.0)
            
        except Exception as e:
            print(f"  ❌ Strategy failed: {e}")
            results[strategy_name] = {"error": str(e)}
    
    # Final analysis
    print(f"\n📊 AGGRESSIVE EXTRACTION RESULTS")
    print("=" * 70)
    
    total_found = 0
    best_strategy = None
    best_count = 0
    
    for strategy, result in results.items():
        if isinstance(result, dict) and 'private_count' in result:
            count = result['private_count']
            total_found += count
            print(f"  {strategy}: {count} private newsletters found")
            
            if count > best_count:
                best_count = count
                best_strategy = strategy
        else:
            print(f"  {strategy}: Failed or no results")
    
    if best_strategy:
        print(f"\n🏆 BEST STRATEGY: {best_strategy}")
        print(f"  🎯 Found: {best_count} private newsletters")
        print(f"  📈 Improvement over current 137: {best_count - 137}")
        
        if best_count > 200:
            print(f"  🚀 RECOMMENDATION: Implement {best_strategy} for full extraction")
    
    return results

def test_all_folder_access(client):
    """Test accessing 'all' folder or no folder parameter"""
    
    print("  🔍 Testing 'all' folder access...")
    
    strategies = [
        {"folder": "all", "limit": 500},
        {"folder": "", "limit": 500}, 
        {"limit": 500},  # No folder parameter
        {"folder": "unread", "limit": 500, "have": ""},  # Empty have parameter
    ]
    
    best_result = {"private_count": 0}
    
    for i, params in enumerate(strategies):
        try:
            print(f"    Testing variant {i+1}: {params}")
            
            url = client.BASE_URL + "bookmarks/list"
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
                
                print(f"      ✅ Found {private_count} private newsletters, {len(bookmarks)} total")
                
                if private_count > best_result['private_count']:
                    best_result = {
                        'private_count': private_count,
                        'total_bookmarks': len(bookmarks),
                        'variant': i+1,
                        'params': params
                    }
            else:
                print(f"      ❌ API failed: {response.status_code}")
                
            time.sleep(1.0)
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    return best_result

def test_archive_folder(client):
    """Test archive folder for additional private content"""
    
    print("  🔍 Testing archive folder...")
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': 'archive'}
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
            
            print(f"    ✅ Archive folder: {private_count} private, {len(bookmarks)} total")
            
            return {
                'private_count': private_count,
                'total_bookmarks': len(bookmarks),
                'folder': 'archive'
            }
        else:
            print(f"    ❌ Archive folder failed: {response.status_code}")
            
    except Exception as e:
        print(f"    ❌ Archive folder error: {e}")
    
    return {"private_count": 0}

def test_starred_folder(client):
    """Test starred folder"""
    
    print("  🔍 Testing starred folder...")
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': 'starred'}
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
            
            print(f"    ✅ Starred folder: {private_count} private, {len(bookmarks)} total")
            
            return {
                'private_count': private_count,
                'total_bookmarks': len(bookmarks),
                'folder': 'starred'
            }
        else:
            print(f"    ❌ Starred folder failed: {response.status_code}")
            
    except Exception as e:
        print(f"    ❌ Starred folder error: {e}")
    
    return {"private_count": 0}

def test_pagination_variants(client):
    """Test different pagination approaches"""
    
    print("  🔍 Testing pagination variants...")
    
    unique_private = set()
    
    # Get first batch
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': 'unread'}
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
                        unique_private.add(bookmark_id)
            
            print(f"    ✅ First batch: {len(unique_private)} unique private")
            
            if bookmarks:
                # Try pagination with last bookmark ID
                last_bookmark_id = bookmarks[-1].get('bookmark_id')
                
                if last_bookmark_id:
                    print(f"    🔄 Testing pagination from ID: {last_bookmark_id}")
                    
                    params_next = {'limit': 500, 'folder': 'unread', 'have': last_bookmark_id}
                    response_next = client.oauth.post(url, data=params_next)
                    
                    if response_next.status_code == 200:
                        next_bookmarks = response_next.json()
                        print(f"      📊 Next batch size: {len(next_bookmarks)}")
                        
                        for bookmark in next_bookmarks:
                            if bookmark.get('type') == 'bookmark':
                                bookmark_url = bookmark.get('url', '')
                                private_source = bookmark.get('private_source', '')
                                bookmark_id = bookmark.get('bookmark_id')
                                
                                is_private = ('instapaper-private' in bookmark_url or 
                                            private_source or 
                                            bookmark_url.startswith('instapaper://private'))
                                
                                if is_private and bookmark_id:
                                    unique_private.add(bookmark_id)
                        
                        print(f"      ✅ After pagination: {len(unique_private)} unique private total")
                    else:
                        print(f"      ❌ Pagination failed: {response_next.status_code}")
                        
    except Exception as e:
        print(f"    ❌ Pagination test error: {e}")
    
    return {
        'private_count': len(unique_private),
        'method': 'pagination_with_have_param'
    }

def test_batch_bookmark_access(client):
    """Test accessing bookmarks by batch IDs"""
    
    print("  🔍 Testing batch bookmark ID access...")
    
    # This would require having bookmark IDs from CSV
    # For now, just test the endpoint exists
    
    try:
        # Test if we can get bookmark details by ID
        url = client.BASE_URL + "bookmarks/get_text"
        
        # Use a known bookmark ID from our previous extractions
        test_id = "1648758187"  # Example ID
        params = {'bookmark_id': test_id}
        
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            content = response.text
            print(f"    ✅ Bookmark ID access works: {len(content)} chars")
            return {'private_count': 1, 'method': 'direct_id_access'}
        else:
            print(f"    ❌ Bookmark ID access failed: {response.status_code}")
            
    except Exception as e:
        print(f"    ❌ Batch access error: {e}")
    
    return {"private_count": 0}

def test_private_url_patterns(client):
    """Test different private URL pattern handling"""
    
    print("  🔍 Testing private URL patterns...")
    
    # This is more of an analysis function
    patterns_found = {
        'instapaper_private_email': 0,
        'instapaper_private_content': 0,
        'private_source_email': 0,
        'other_private': 0
    }
    
    try:
        url = client.BASE_URL + "bookmarks/list"
        params = {'limit': 500, 'folder': 'unread'}
        response = client.oauth.post(url, data=params)
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            for bookmark in bookmarks:
                if bookmark.get('type') == 'bookmark':
                    bookmark_url = bookmark.get('url', '')
                    private_source = bookmark.get('private_source', '')
                    
                    if 'instapaper-private://email/' in bookmark_url:
                        patterns_found['instapaper_private_email'] += 1
                    elif 'instapaper://private-content/' in bookmark_url:
                        patterns_found['instapaper_private_content'] += 1
                    elif private_source == 'email':
                        patterns_found['private_source_email'] += 1
                    elif private_source or 'private' in bookmark_url:
                        patterns_found['other_private'] += 1
            
            total_private = sum(patterns_found.values())
            
            print(f"    📊 Private URL patterns found:")
            for pattern, count in patterns_found.items():
                if count > 0:
                    print(f"      {pattern}: {count}")
            
            return {
                'private_count': total_private,
                'patterns': patterns_found
            }
            
    except Exception as e:
        print(f"    ❌ Pattern analysis error: {e}")
    
    return {"private_count": 0}

if __name__ == '__main__':
    results = aggressive_private_extraction()
    
    # Save results
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_file = f"aggressive_extraction_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Results saved: {results_file}")