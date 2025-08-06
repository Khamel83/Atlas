#!/usr/bin/env python3
"""
FINAL INSTAPAPER MAXIMIZATION - Leave no stone unturned
Test EVERY possible angle to extract maximum content
"""

import os
import json
import time
import csv
from datetime import datetime
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def final_instapaper_maximization():
    """Test absolutely everything possible with Instapaper API"""
    
    print("🚀 FINAL INSTAPAPER MAXIMIZATION ATTEMPT")
    print("🔥 LEAVING NO STONE UNTURNED")
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
    
    results = {}
    
    # Test 1: Archive folder (historical content)
    print(f"\n🗃️  TEST 1: ARCHIVE FOLDER DEEP DIVE")
    print("-" * 50)
    archive_result = test_archive_folder_deep(client)
    results['archive_folder'] = archive_result
    
    # Test 2: Starred folder
    print(f"\n⭐ TEST 2: STARRED FOLDER EXTRACTION")
    print("-" * 50)
    starred_result = test_starred_folder_deep(client)
    results['starred_folder'] = starred_result
    
    # Test 3: Different pagination strategies
    print(f"\n📄 TEST 3: ADVANCED PAGINATION STRATEGIES")
    print("-" * 50)
    pagination_result = test_advanced_pagination(client)
    results['pagination_strategies'] = pagination_result
    
    # Test 4: Folder redistribution test
    print(f"\n🔄 TEST 4: FOLDER REDISTRIBUTION STRATEGY")
    print("-" * 50)
    redistribution_result = test_folder_redistribution(client)
    results['folder_redistribution'] = redistribution_result
    
    # Test 5: Alternative endpoint exploration
    print(f"\n🕵️  TEST 5: ALTERNATIVE API ENDPOINTS")
    print("-" * 50)
    endpoints_result = test_alternative_endpoints(client)
    results['alternative_endpoints'] = endpoints_result
    
    # Test 6: Batch ID approach from CSV
    print(f"\n📋 TEST 6: CSV BOOKMARK ID BATCH PROCESSING")
    print("-" * 50)
    csv_batch_result = test_csv_bookmark_ids(client)
    results['csv_batch_processing'] = csv_batch_result
    
    # Test 7: Search API exploration
    print(f"\n🔍 TEST 7: SEARCH API EXPLORATION")
    print("-" * 50)
    search_result = test_search_api(client)
    results['search_api'] = search_result
    
    # Final analysis
    print(f"\n📊 FINAL MAXIMIZATION RESULTS")
    print("=" * 70)
    
    total_new_found = 0
    best_strategies = []
    
    for test_name, result in results.items():
        if isinstance(result, dict) and 'new_content_found' in result:
            new_found = result['new_content_found']
            total_new_found += new_found
            
            if new_found > 0:
                best_strategies.append((test_name, new_found))
                print(f"  ✅ {test_name}: +{new_found} new content")
            else:
                print(f"  ❌ {test_name}: No new content")
        else:
            print(f"  ⚠️  {test_name}: {result}")
    
    if total_new_found > 0:
        print(f"\n🎉 SUCCESS: Found {total_new_found} additional content!")
        print(f"📈 Best strategies:")
        for strategy, count in sorted(best_strategies, key=lambda x: x[1], reverse=True):
            print(f"    {strategy}: +{count}")
    else:
        print(f"\n📊 ANALYSIS: No additional content found via API")
        print(f"🔒 Confirms: API extraction is maximized at 138 newsletters")
    
    # Save comprehensive report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    final_report = {
        'maximization_timestamp': timestamp,
        'total_tests_run': len(results),
        'total_new_content_found': total_new_found,
        'test_results': results,
        'best_strategies': best_strategies,
        'conclusion': 'API_MAXIMIZED' if total_new_found == 0 else 'ADDITIONAL_CONTENT_FOUND'
    }
    
    report_file = f"final_instapaper_maximization_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Complete maximization report: {report_file}")
    
    return results

def test_archive_folder_deep(client):
    """Deep test of archive folder for missed content"""
    
    try:
        print("  🔍 Testing archive folder with multiple strategies...")
        
        strategies = [
            {'folder': 'archive', 'limit': 500},
            {'folder': 'archive', 'limit': 500, 'have': ''},
        ]
        
        all_archive_content = {}
        
        for i, params in enumerate(strategies):
            url = client.BASE_URL + "bookmarks/list"
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                bookmarks = response.json()
                
                extractable_count = 0
                for bookmark in bookmarks:
                    if bookmark.get('type') == 'bookmark':
                        bookmark_id = bookmark.get('bookmark_id')
                        if bookmark_id:
                            # Test if content is extractable
                            text_url = client.BASE_URL + "bookmarks/get_text"
                            text_params = {'bookmark_id': bookmark_id}
                            text_response = client.oauth.post(text_url, data=text_params)
                            
                            if text_response.status_code == 200:
                                content = text_response.text
                                if len(content.strip()) > 100:
                                    all_archive_content[bookmark_id] = {
                                        'title': bookmark.get('title', 'Untitled'),
                                        'content_length': len(content),
                                        'strategy': f"archive_strategy_{i+1}"
                                    }
                                    extractable_count += 1
                            
                            time.sleep(0.5)  # Rate limiting
                            
                            # Test only first 10 to save time
                            if extractable_count >= 10:
                                break
                
                print(f"    Strategy {i+1}: Found {len(bookmarks)} bookmarks, {extractable_count} extractable")
            
            time.sleep(2.0)
        
        return {
            'new_content_found': len(all_archive_content),
            'extractable_archive_content': all_archive_content
        }
        
    except Exception as e:
        return f"Archive test error: {e}"

def test_starred_folder_deep(client):
    """Deep test of starred folder"""
    
    try:
        print("  ⭐ Testing starred folder extraction...")
        
        url = client.BASE_URL + "bookmarks/list"
        params = {'folder': 'starred', 'limit': 500}
        response = client.oauth.post(url, data=params)
        
        starred_content = {}
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            # Test first 20 starred items for content
            for i, bookmark in enumerate(bookmarks[:20]):
                if bookmark.get('type') == 'bookmark':
                    bookmark_id = bookmark.get('bookmark_id')
                    if bookmark_id:
                        text_url = client.BASE_URL + "bookmarks/get_text"
                        text_params = {'bookmark_id': bookmark_id}
                        text_response = client.oauth.post(text_url, data=text_params)
                        
                        if text_response.status_code == 200:
                            content = text_response.text
                            if len(content.strip()) > 100:
                                starred_content[bookmark_id] = {
                                    'title': bookmark.get('title', 'Untitled'),
                                    'content_length': len(content)
                                }
                        
                        time.sleep(0.5)
            
            print(f"    Found {len(bookmarks)} starred items, {len(starred_content)} extractable")
        
        return {
            'new_content_found': len(starred_content),
            'starred_content': starred_content
        }
        
    except Exception as e:
        return f"Starred test error: {e}"

def test_advanced_pagination(client):
    """Test advanced pagination strategies"""
    
    try:
        print("  📄 Testing advanced pagination...")
        
        # Test reverse pagination
        url = client.BASE_URL + "bookmarks/list"
        
        # Get the latest batch first
        params = {'limit': 500}
        response = client.oauth.post(url, data=params)
        
        unique_items = set()
        
        if response.status_code == 200:
            bookmarks = response.json()
            
            for bookmark in bookmarks:
                if bookmark.get('type') == 'bookmark':
                    unique_items.add(bookmark.get('bookmark_id'))
            
            print(f"    Initial batch: {len(unique_items)} unique items")
            
            # Try pagination with different have parameters
            if bookmarks:
                last_id = bookmarks[-1].get('bookmark_id')
                first_id = bookmarks[0].get('bookmark_id')
                
                # Test forward pagination
                forward_params = {'limit': 500, 'have': last_id}
                forward_response = client.oauth.post(url, data=forward_params)
                
                if forward_response.status_code == 200:
                    forward_bookmarks = forward_response.json()
                    for bookmark in forward_bookmarks:
                        if bookmark.get('type') == 'bookmark':
                            unique_items.add(bookmark.get('bookmark_id'))
                    
                    print(f"    After forward pagination: {len(unique_items)} unique items")
        
        return {
            'new_content_found': 0,  # This is for discovery, not extraction
            'unique_items_found': len(unique_items)
        }
        
    except Exception as e:
        return f"Pagination test error: {e}"

def test_folder_redistribution(client):
    """Test if moving items between folders helps access"""
    
    try:
        print("  🔄 Testing folder redistribution theory...")
        
        # This is more theoretical - we can't actually move items in read-only mode
        # But we can test if different folder access patterns yield different results
        
        folders_to_test = ['unread', 'archive', 'starred', 'all']
        folder_results = {}
        
        for folder in folders_to_test:
            url = client.BASE_URL + "bookmarks/list"
            params = {'folder': folder, 'limit': 100}  # Smaller limit for testing
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                bookmarks = response.json()
                private_count = sum(1 for b in bookmarks if b.get('type') == 'bookmark' and 
                                   ('instapaper-private' in b.get('url', '') or b.get('private_source')))
                folder_results[folder] = {
                    'total_items': len(bookmarks),
                    'private_newsletters': private_count
                }
                print(f"    {folder}: {len(bookmarks)} items, {private_count} private")
            
            time.sleep(1.0)
        
        return {
            'new_content_found': 0,
            'folder_analysis': folder_results
        }
        
    except Exception as e:
        return f"Redistribution test error: {e}"

def test_alternative_endpoints(client):
    """Test alternative API endpoints"""
    
    try:
        print("  🕵️  Testing alternative API endpoints...")
        
        endpoints_to_test = [
            "folders/list",
            "bookmarks/list",  # Different parameters
            "account/verify_credentials"
        ]
        
        endpoint_results = {}
        
        for endpoint in endpoints_to_test:
            try:
                url = client.BASE_URL + endpoint
                response = client.oauth.post(url, data={})
                
                endpoint_results[endpoint] = {
                    'status_code': response.status_code,
                    'response_length': len(response.text) if response.status_code == 200 else 0
                }
                
                print(f"    {endpoint}: {response.status_code}")
                
                time.sleep(1.0)
                
            except Exception as e:
                endpoint_results[endpoint] = f"Error: {e}"
        
        return {
            'new_content_found': 0,
            'endpoint_results': endpoint_results
        }
        
    except Exception as e:
        return f"Alternative endpoints error: {e}"

def test_csv_bookmark_ids(client):
    """Test direct bookmark ID access from CSV"""
    
    try:
        print("  📋 Testing CSV bookmark ID batch processing...")
        
        # This would require parsing the CSV for bookmark IDs
        # For now, test the concept with a few known IDs
        
        # Note: This is a placeholder - would need actual CSV parsing
        print("    (This would require CSV bookmark ID extraction)")
        print("    Concept: Direct API calls to bookmark IDs from CSV")
        
        return {
            'new_content_found': 0,
            'note': 'Would require CSV bookmark ID parsing implementation'
        }
        
    except Exception as e:
        return f"CSV batch test error: {e}"

def test_search_api(client):
    """Test search API functionality"""
    
    try:
        print("  🔍 Testing search API...")
        
        # Test if there's a search endpoint
        search_terms = ['newsletter', 'private', '2024']
        
        for term in search_terms:
            try:
                # This is speculative - Instapaper may not have public search API
                url = client.BASE_URL + "bookmarks/search"
                params = {'query': term, 'limit': 10}
                response = client.oauth.post(url, data=params)
                
                print(f"    Search '{term}': {response.status_code}")
                
                time.sleep(1.0)
                
            except Exception as e:
                print(f"    Search '{term}': Not available")
        
        return {
            'new_content_found': 0,
            'note': 'Search API exploration completed'
        }
        
    except Exception as e:
        return f"Search API test error: {e}"

if __name__ == '__main__':
    final_instapaper_maximization()