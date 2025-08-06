#!/usr/bin/env python3
"""
Test script for Instapaper API authentication using proper xAuth flow
"""

import os
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv()

# OAuth credentials from .env
CONSUMER_KEY = os.getenv('INSTAPAPER_CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('INSTAPAPER_CONSUMER_SECRET')
USERNAME = os.getenv('INSTAPAPER_USERNAME')  
PASSWORD = os.getenv('INSTAPAPER_PASSWORD')

print(f"Using consumer key: {CONSUMER_KEY}")
print(f"Using username: {USERNAME}")

def test_instapaper_auth():
    """Test Instapaper xAuth authentication flow"""
    
    # Step 1: Create OAuth1Session for xAuth token request
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        signature_method='HMAC-SHA1'
    )
    
    # Step 2: Request access token using xAuth
    token_url = 'https://www.instapaper.com/api/1/oauth/access_token'
    
    # xAuth parameters as specified in documentation
    xauth_data = {
        'x_auth_username': USERNAME,
        'x_auth_password': PASSWORD,
        'x_auth_mode': 'client_auth'
    }
    
    print("Requesting access token...")
    try:
        response = oauth.post(token_url, data=xauth_data)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            # Parse token response
            token_data = dict(item.split('=') for item in response.text.split('&'))
            access_token = token_data.get('oauth_token')
            access_token_secret = token_data.get('oauth_token_secret')
            
            print(f"Access token: {access_token}")
            print(f"Access secret: {access_token_secret}")
            
            if access_token and access_token_secret:
                # Step 3: Test authenticated request
                return test_api_call(access_token, access_token_secret)
        else:
            print(f"Authentication failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error during authentication: {e}")
        return False

def test_api_call(access_token, access_token_secret):
    """Test an API call with the obtained tokens"""
    
    # Create authenticated session
    auth_session = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
        signature_method='HMAC-SHA1'
    )
    
    # Test endpoint: verify credentials
    test_url = 'https://www.instapaper.com/api/1/account/verify_credentials'
    
    print("Testing authenticated API call...")
    try:
        response = auth_session.post(test_url)
        print(f"API call status: {response.status_code}")
        print(f"API response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Authentication successful!")
            
            # Now test bookmark listing
            bookmarks_url = 'https://www.instapaper.com/api/1/bookmarks/list'
            bookmark_response = auth_session.post(bookmarks_url, data={'limit': 5})
            print(f"Bookmarks status: {bookmark_response.status_code}")
            if bookmark_response.status_code == 200:
                print(f"✅ Got bookmarks! Sample: {bookmark_response.text[:200]}...")
                return True
            else:
                print(f"❌ Bookmarks failed: {bookmark_response.text}")
        else:
            print(f"❌ API call failed: {response.text}")
            
    except Exception as e:
        print(f"Error during API call: {e}")
        
    return False

if __name__ == '__main__':
    if not all([CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD]):
        print("❌ Missing credentials in .env file")
        exit(1)
        
    success = test_instapaper_auth()
    if success:
        print("🎉 Instapaper API integration working!")
    else:
        print("💥 Authentication still failing - need to investigate further")