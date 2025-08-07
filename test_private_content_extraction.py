#!/usr/bin/env python3
"""
Test if we can extract private newsletter content using various Instapaper API approaches
"""

import os
import csv
import re
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def test_private_content_extraction():
    """Test different approaches to get private content from Instapaper"""
    
    load_dotenv()
    
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing Instapaper credentials")
        return
    
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print()
    
    print("🔍 TESTING PRIVATE CONTENT EXTRACTION METHODS")
    print("=" * 60)
    
    # Test 1: Check if private content appears in any folder
    print("📁 TEST 1: Searching all folders for private content")
    print("-" * 40)
    
    folders_to_test = ['unread', 'archive', 'starred']
    found_private_in_api = False
    
    for folder in folders_to_test:
        print(f"  Checking {folder} folder...")
        try:
            url = client.BASE_URL + "bookmarks/list"
            params = {'limit': 100, 'folder': folder}
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                bookmarks = response.json()
                private_count = 0
                
                for bookmark in bookmarks:
                    if bookmark.get('type') == 'bookmark':
                        url_val = bookmark.get('url', '')
                        if 'instapaper-private' in url_val or bookmark.get('private_source'):
                            private_count += 1
                            found_private_in_api = True
                            print(f"    Found private: {bookmark.get('title', 'No title')[:50]}")
                
                print(f"    Private items found: {private_count}")
            
        except Exception as e:
            print(f"    Error: {e}")
    
    if not found_private_in_api:
        print("  ❌ No private content found in API responses")
    
    print()
    
    # Test 2: Try to extract content using hash IDs from CSV
    print("📧 TEST 2: Attempt content extraction using CSV private URLs")
    print("-" * 40)
    
    # Get some private content entries from CSV
    csv_file = "inputs/instapaper_export.csv"
    private_samples = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                url = row.get('URL', '')
                if url.startswith('instapaper-private://') and len(private_samples) < 5:
                    private_samples.append({
                        'url': url,
                        'title': row.get('Title', 'No title'),
                        'timestamp': row.get('Timestamp', ''),
                        'selection': row.get('Selection', '')
                    })
    except Exception as e:
        print(f"  ❌ Error reading CSV: {e}")
        return
    
    print(f"  Testing with {len(private_samples)} private content samples:")
    
    for i, sample in enumerate(private_samples):
        print(f"\n  Sample {i+1}: {sample['title'][:50]}")
        print(f"    URL: {sample['url']}")
        
        # Extract hash from private URL
        hash_match = re.search(r'instapaper-private://email/([^/]+)/', sample['url'])
        if hash_match:
            hash_id = hash_match.group(1)
            print(f"    Hash ID: {hash_id}")
            
            # Test different API approaches
            success = False
            
            # Approach 1: Try using hash as bookmark_id
            try:
                test_url = client.BASE_URL + "bookmarks/get_text"
                params = {'bookmark_id': hash_id}
                response = client.oauth.post(test_url, data=params)
                
                if response.status_code == 200 and len(response.text) > 100:
                    print(f"    ✅ SUCCESS with hash as bookmark_id! Content length: {len(response.text)}")
                    print(f"    Sample content: {response.text[:100]}...")
                    success = True
                else:
                    print(f"    ❌ Failed with hash as bookmark_id (status: {response.status_code})")
                    
            except Exception as e:
                print(f"    ❌ Error with hash approach: {e}")
            
            # Approach 2: Try different parameter names
            if not success:
                for param_name in ['hash', 'private_id', 'content_id']:
                    try:
                        test_url = client.BASE_URL + "bookmarks/get_text"
                        params = {param_name: hash_id}
                        response = client.oauth.post(test_url, data=params)
                        
                        if response.status_code == 200 and len(response.text) > 100:
                            print(f"    ✅ SUCCESS with {param_name}! Content length: {len(response.text)}")
                            success = True
                            break
                        else:
                            print(f"    ❌ Failed with {param_name} (status: {response.status_code})")
                            
                    except Exception as e:
                        print(f"    ❌ Error with {param_name}: {e}")
            
            if not success:
                # Check if CSV Selection field has content
                if sample['selection']:
                    print(f"    💡 CSV has Selection content: {len(sample['selection'])} chars")
                    print(f"        Selection preview: {sample['selection'][:100]}...")
                else:
                    print(f"    ❌ No API access and no CSV Selection content")
    
    print()
    
    # Test 3: Check for other API endpoints
    print("🔍 TEST 3: Exploring other potential API endpoints")
    print("-" * 40)
    
    endpoints_to_test = [
        'bookmarks/private',
        'emails/list', 
        'newsletters/list',
        'private/list',
        'content/private'
    ]
    
    for endpoint in endpoints_to_test:
        try:
            test_url = client.BASE_URL + endpoint
            response = client.oauth.post(test_url, data={'limit': 5})
            
            if response.status_code == 200:
                print(f"    ✅ {endpoint} exists! Response: {len(response.text)} chars")
                if len(response.text) < 500:
                    print(f"        Content: {response.text}")
            elif response.status_code == 404:
                print(f"    ❌ {endpoint} - Not found")
            else:
                print(f"    ⚠️  {endpoint} - Status {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ {endpoint} - Error: {e}")
    
    print()
    
    # Summary and recommendations
    print("🎯 SUMMARY & RECOMMENDATIONS")
    print("=" * 60)
    
    print("Based on testing:")
    
    if found_private_in_api:
        print("✅ Private content IS accessible via API")
        print("💡 Recommend: Extract private content using API methods")
    else:
        print("❌ Private content NOT found in API responses")
    
    # Check CSV Selection content
    selection_count = sum(1 for s in private_samples if s['selection'])
    print(f"📊 CSV Selection field has content in {selection_count}/{len(private_samples)} samples")
    
    if selection_count > 0:
        print("💡 CSV Selection field contains some newsletter content")
        print("🔧 Current approach: Use CSV Selection content (partial)")
        print("🎯 Better approach: Investigate API private content endpoints")
    
    print(f"\nTotal private items to potentially recover: 2,769")

if __name__ == '__main__':
    test_private_content_extraction()