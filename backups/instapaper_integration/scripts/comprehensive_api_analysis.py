#!/usr/bin/env python3
"""
Comprehensive analysis of the Instapaper API discrepancy and subscription impact
"""

import os
import json
from dotenv import load_dotenv
from helpers.instapaper_api_client import InstapaperAPIClient

def comprehensive_api_analysis():
    """Analyze the API behavior with subscription account"""
    
    load_dotenv()
    
    # Load credentials
    consumer_key = os.getenv('INSTAPAPER_CONSUMER_KEY')
    consumer_secret = os.getenv('INSTAPAPER_CONSUMER_SECRET')
    username = os.getenv('INSTAPAPER_USERNAME')
    password = os.getenv('INSTAPAPER_PASSWORD')
    
    if not all([consumer_key, consumer_secret, username, password]):
        print("❌ Missing Instapaper credentials in .env file")
        return
    
    print("🔍 COMPREHENSIVE INSTAPAPER API ANALYSIS")
    print("=" * 60)
    
    # Initialize client
    client = InstapaperAPIClient(consumer_key, consumer_secret)
    
    # Authenticate
    print("🔐 Authenticating...")
    if not client.authenticate(username, password):
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    print()
    
    # Get account info first
    print("📊 ACCOUNT STATUS ANALYSIS")
    print("-" * 40)
    
    try:
        url = client.BASE_URL + "account/verify_credentials"
        response = client.oauth.post(url)
        
        if response.status_code == 200:
            account_info = response.json()
            subscription_active = account_info[0].get('subscription_is_active', 0)
            account_type = account_info[0].get('type', 'unknown')
            
            print(f"  ✅ Subscription Status: {'ACTIVE' if subscription_active else 'INACTIVE'}")
            print(f"  Account Type: {account_type}")
            print()
            
            # This is KEY - subscription is ACTIVE now!
            if subscription_active:
                print("  🎯 KEY FINDING: You have an ACTIVE subscription!")
                print("     This explains the API behavior difference!")
                print()
        else:
            print(f"  ❌ Failed to get account info: {response.status_code}")
            return
    except Exception as e:
        print(f"  ❌ Error getting account info: {e}")
        return
    
    # Now test all folders with subscription access
    print("📁 FOLDER ANALYSIS WITH SUBSCRIPTION ACCESS")
    print("-" * 50)
    
    folder_types = {
        'unread': 'Unread',
        'archive': 'Archive', 
        'starred': 'Starred'
    }
    
    # Add custom folders
    try:
        folders_url = client.BASE_URL + "folders/list"
        folders_response = client.oauth.post(folders_url)
        
        if folders_response.status_code == 200:
            custom_folders = folders_response.json()
            for folder in custom_folders:
                folder_id = folder.get('folder_id')
                title = folder.get('display_title', folder.get('title', 'Untitled'))
                folder_types[str(folder_id)] = title
    except Exception as e:
        print(f"  ⚠️  Could not get custom folders: {e}")
    
    total_unique_bookmarks = set()
    folder_results = {}
    
    for folder_key, folder_name in folder_types.items():
        print(f"  📂 Testing folder: {folder_name} ({folder_key})")
        
        try:
            # Test with maximum limit
            url = client.BASE_URL + "bookmarks/list"
            params = {'limit': 500, 'folder': folder_key}
            response = client.oauth.post(url, data=params)
            
            if response.status_code == 200:
                bookmarks = response.json()
                bookmark_count = len(bookmarks)
                
                # Extract bookmark IDs for uniqueness tracking
                bookmark_ids = set()
                for bookmark in bookmarks:
                    if bookmark.get('bookmark_id'):
                        bookmark_ids.add(bookmark['bookmark_id'])
                        total_unique_bookmarks.add(bookmark['bookmark_id'])
                
                folder_results[folder_name] = {
                    'count': bookmark_count,
                    'unique_ids': len(bookmark_ids),
                    'at_limit': bookmark_count == 500
                }
                
                print(f"    ✅ Retrieved: {bookmark_count} bookmarks")
                print(f"    Unique IDs: {len(bookmark_ids)}")
                
                if bookmark_count == 500:
                    print(f"    ⚠️  AT 500 LIMIT - May have more!")
                    
                    # Test pagination for folders at limit
                    print(f"    🔄 Testing pagination...")
                    
                    bookmark_ids_list = [str(b.get('bookmark_id')) for b in bookmarks if b.get('bookmark_id')]
                    have_param = ','.join(bookmark_ids_list)
                    
                    params_with_have = {
                        'limit': 500,
                        'folder': folder_key,
                        'have': have_param
                    }
                    
                    response2 = client.oauth.post(url, data=params_with_have)
                    
                    if response2.status_code == 200:
                        next_bookmarks = response2.json()
                        print(f"    📄 Page 2: {len(next_bookmarks)} additional bookmarks")
                        
                        if len(next_bookmarks) > 0:
                            # Add to totals
                            next_ids = set()
                            for bookmark in next_bookmarks:
                                if bookmark.get('bookmark_id'):
                                    next_ids.add(bookmark['bookmark_id'])
                                    total_unique_bookmarks.add(bookmark['bookmark_id'])
                            
                            folder_results[folder_name]['page2_count'] = len(next_bookmarks)
                            folder_results[folder_name]['page2_unique'] = len(next_ids)
                            
                            # Check for overlap
                            overlap = bookmark_ids & next_ids
                            print(f"    Overlap: {len(overlap)} bookmarks")
                            
                            if len(next_bookmarks) == 500:
                                print(f"    🔄 Page 2 also at limit - could continue...")
                        else:
                            print(f"    ✅ No more bookmarks in this folder")
                    else:
                        print(f"    ❌ Page 2 failed: {response2.status_code}")
                else:
                    print(f"    ✅ Got all bookmarks from this folder")
                
            else:
                print(f"    ❌ Failed: {response.status_code} - {response.text}")
                folder_results[folder_name] = {'count': 0, 'error': response.status_code}
        
        except Exception as e:
            print(f"    ❌ Error: {e}")
            folder_results[folder_name] = {'count': 0, 'error': str(e)}
        
        print()
    
    # Summary
    print("🎯 COMPREHENSIVE ANALYSIS SUMMARY")
    print("=" * 60)
    
    total_bookmarks = sum(r.get('count', 0) for r in folder_results.values())
    folders_at_limit = sum(1 for r in folder_results.values() if r.get('at_limit', False))
    
    print(f"📊 TOTALS:")
    print(f"  Total bookmarks retrieved: {total_bookmarks:,}")
    print(f"  Unique bookmark IDs: {len(total_unique_bookmarks):,}")
    print(f"  Folders at 500 limit: {folders_at_limit}")
    print()
    
    print(f"📁 FOLDER BREAKDOWN:")
    for folder_name, results in folder_results.items():
        if 'error' in results:
            print(f"  {folder_name:15} | ERROR: {results['error']}")
        else:
            count = results['count']
            page2_count = results.get('page2_count', 0)
            total_folder = count + page2_count
            status = "📍 AT LIMIT" if results.get('at_limit') else "✅ Complete"
            
            print(f"  {folder_name:15} | {total_folder:4,} bookmarks | {status}")
            
            if page2_count > 0:
                print(f"  {' '*15} | (Page 1: {count}, Page 2: {page2_count})")
    
    print()
    
    # Load previous CSV comparison data
    csv_file = "inputs/instapaper_export.csv"
    if os.path.exists(csv_file):
        print("📋 COMPARISON WITH CSV EXPORT:")
        print("-" * 40)
        
        # Count CSV lines
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                csv_lines = sum(1 for line in f) - 1  # Subtract header
            
            print(f"  CSV export contains: {csv_lines:,} bookmarks")
            print(f"  API retrieved: {len(total_unique_bookmarks):,} unique bookmarks")
            
            coverage = len(total_unique_bookmarks) / csv_lines * 100 if csv_lines > 0 else 0
            print(f"  API Coverage: {coverage:.1f}%")
            
            if coverage > 50:
                print(f"  ✅ MUCH BETTER coverage with subscription!")
            else:
                print(f"  ⚠️  Still significant gap...")
                
        except Exception as e:
            print(f"  ❌ Could not read CSV file: {e}")
    
    print()
    
    # Key findings
    print("🔑 KEY FINDINGS:")
    print("-" * 40)
    
    if subscription_active:
        print("  ✅ SUBSCRIPTION IS ACTIVE - This changes everything!")
        print("  💡 Your active subscription should provide full API access")
        print("  🔍 If we're still missing bookmarks, it may be due to:")
        print("     - Pagination implementation needs improvement")
        print("     - Some folders weren't fully extracted")
        print("     - Historical data limitations")
    else:
        print("  ❌ Free tier limitations confirmed")
    
    print()
    
    # Recommendations
    print("💡 RECOMMENDATIONS:")
    print("-" * 40)
    
    if folders_at_limit > 0:
        print("  🔄 PAGINATION NEEDED:")
        print("     Several folders hit the 500-bookmark limit")
        print("     Implement proper pagination to extract ALL bookmarks")
        print()
    
    if len(total_unique_bookmarks) < 6000:  # Based on CSV having 6,233
        print("  📈 EXTRACTION IMPROVEMENT NEEDED:")
        print("     1. Implement full pagination for all folders")
        print("     2. Continue pagination until no more bookmarks")
        print("     3. Test with smaller batch sizes if needed")
        print("     4. Verify all folder types are being checked")
        print()
    
    print("  🎯 NEXT STEPS:")
    print("     1. Implement robust pagination for subscription accounts")
    print("     2. Extract ALL bookmarks using proper pagination")
    print("     3. Compare final results with CSV export")
    print("     4. You should be able to get your complete collection!")

if __name__ == '__main__':
    comprehensive_api_analysis()