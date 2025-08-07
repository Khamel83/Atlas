#!/usr/bin/env python3
"""
Check Instapaper account status and API limitations
"""

import json
import os
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

load_dotenv()

def check_account_status():
    """Check account details and subscription status"""
    
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
    
    # Check account details
    print("🔍 CHECKING ACCOUNT STATUS...")
    check_verify_credentials(client)
    
    # Test API limits with debug info
    print("\n🔍 TESTING API BEHAVIOR...")
    test_api_limits(client)

def check_verify_credentials(client):
    """Check account credentials and subscription status"""
    
    url = client.BASE_URL + "account/verify_credentials"
    
    try:
        response = client.oauth.post(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"Account info: {data}")
        
        if isinstance(data, list) and len(data) > 0:
            user_info = data[0] if data[0].get('type') == 'user' else None
            
            if user_info:
                print(f"👤 Username: {user_info.get('username')}")
                print(f"🆔 User ID: {user_info.get('user_id')}")
                print(f"💳 Subscription Active: {user_info.get('subscription_is_active')}")
                
                # Check if subscription affects API access
                subscription_active = user_info.get('subscription_is_active')
                if subscription_active == '0':
                    print("⚠️  WARNING: Subscription is not active - this might limit API access!")
                else:
                    print("✅ Subscription is active")
                    
        else:
            print(f"Unexpected account response format: {data}")
            
    except Exception as e:
        print(f"❌ Error checking account: {e}")

def test_api_limits(client):
    """Test various API behaviors to understand limitations"""
    
    print("Testing unread folder with different limits:")
    
    # Test different limit values
    limits_to_test = [10, 50, 100, 500, 1000]
    
    for limit in limits_to_test:
        url = client.BASE_URL + "bookmarks/list"
        params = {
            'limit': limit,
            'folder': 'unread'
        }
        
        try:
            response = client.oauth.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            bookmarks = [item for item in data if item.get('type') == 'bookmark']
            
            print(f"  Limit {limit:4d}: Got {len(bookmarks)} bookmarks")
            
            # Check if we got exactly what we asked for
            if len(bookmarks) < limit:
                print(f"    ^ This might be the actual total in this folder")
                
        except Exception as e:
            print(f"  Limit {limit:4d}: Error - {e}")
    
    print("\nTesting archive folder pagination behavior:")
    
    # Test if pagination works at all
    url = client.BASE_URL + "bookmarks/list"
    
    # First request - no 'have' parameter
    params1 = {'limit': 5, 'folder': 'archive'}
    
    try:
        response1 = client.oauth.post(url, data=params1)
        response1.raise_for_status()
        data1 = response1.json()
        bookmarks1 = [item for item in data1 if item.get('type') == 'bookmark']
        
        if bookmarks1:
            first_ids = [str(b['bookmark_id']) for b in bookmarks1]
            print(f"  First 5 bookmark IDs: {first_ids}")
            
            # Second request - with 'have' parameter
            params2 = {
                'limit': 5, 
                'folder': 'archive',
                'have': ','.join(first_ids)
            }
            
            response2 = client.oauth.post(url, data=params2)
            response2.raise_for_status() 
            data2 = response2.json()
            bookmarks2 = [item for item in data2 if item.get('type') == 'bookmark']
            
            if bookmarks2:
                second_ids = [str(b['bookmark_id']) for b in bookmarks2]
                print(f"  Next 5 bookmark IDs: {second_ids}")
                
                # Check for overlap
                overlap = set(first_ids) & set(second_ids)
                if overlap:
                    print(f"  ⚠️  OVERLAP DETECTED: {overlap}")
                    print(f"      This suggests pagination isn't working properly!")
                else:
                    print(f"  ✅ No overlap - pagination might be working")
            else:
                print(f"  📝 No bookmarks in second batch")
                
    except Exception as e:
        print(f"  ❌ Error testing pagination: {e}")

if __name__ == '__main__':
    print("🔍 INSTAPAPER ACCOUNT & API LIMITS INVESTIGATION")
    print("📊 Checking subscription status and API behavior")
    print()
    
    check_account_status()