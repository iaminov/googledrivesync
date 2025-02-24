#!/usr/bin/env python3
"""
Test script for Google Drive & Photos Sync Application
This script tests the basic functionality without running the full sync
"""

import os
import sys
from auth_manager import AuthManager
from drive_manager import DriveManager
from photos_manager import PhotosManager


def test_authentication():
    """Test authentication functionality"""
    print("Testing authentication...")
    
    auth_manager = AuthManager()
    
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("Please follow the setup instructions to create this file.")
        return False
        
    try:
        success = auth_manager.authenticate()
        if success:
            print("✅ Authentication successful!")
            return True
        else:
            print("❌ Authentication failed!")
            return False
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        return False


def test_drive_connection(auth_manager):
    """Test Google Drive connection"""
    print("\nTesting Google Drive connection...")
    
    try:
        drive_manager = DriveManager(auth_manager.get_drive_service())
        
        # Test listing folders
        folders = drive_manager.list_folders()
        print(f"✅ Successfully connected to Google Drive")
        print(f"   Found {len(folders)} folders in root directory")
        
        # Show first few folders
        if folders:
            print("   Sample folders:")
            for folder in folders[:3]:
                print(f"     - {folder['name']}")
                
        return True, drive_manager
        
    except Exception as e:
        print(f"❌ Google Drive connection failed: {str(e)}")
        return False, None


def test_photos_connection(auth_manager):
    """Test Google Photos connection"""
    print("\nTesting Google Photos connection...")
    
    try:
        photos_manager = PhotosManager(auth_manager.get_photos_service())
        
        # Test getting a small sample of media items
        print("   Fetching sample media items...")
        
        # We'll test with a small search to avoid long loading times
        media_items = photos_manager.search_media_items()[:5]  # Just get first 5
        
        print(f"✅ Successfully connected to Google Photos")
        print(f"   Sample media items found: {len(media_items)}")
        
        # Show sample items
        if media_items:
            print("   Sample media files:")
            for item in media_items:
                metadata = photos_manager.parse_media_metadata(item)
                file_type = "Video" if metadata['is_video'] else "Photo"
                print(f"     - {metadata['filename']} ({file_type})")
        
        return True, photos_manager
        
    except Exception as e:
        print(f"❌ Google Photos connection failed: {str(e)}")
        return False, None


def test_file_operations(drive_manager):
    """Test basic file operations"""
    print("\nTesting file operations...")
    
    try:
        # Test getting folder contents for root
        print("   Testing folder content scanning...")
        files = drive_manager.get_folder_contents('root', recursive=False)
        media_files = [f for f in files if drive_manager.is_media_file(f)]
        
        print(f"✅ File operations working")
        print(f"   Total files in root: {len(files)}")
        print(f"   Media files in root: {len(media_files)}")
        
        return True
        
    except Exception as e:
        print(f"❌ File operations failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("🧪 Testing Google Drive & Photos Sync Application")
    print("=" * 50)
    
    # Test 1: Authentication
    auth_manager = AuthManager()
    if not test_authentication():
        print("\n❌ Authentication test failed. Cannot proceed with other tests.")
        return False
        
    # Test 2: Google Drive connection
    drive_success, drive_manager = test_drive_connection(auth_manager)
    if not drive_success:
        print("\n❌ Google Drive test failed.")
        return False
        
    # Test 3: Google Photos connection
    photos_success, photos_manager = test_photos_connection(auth_manager)
    if not photos_success:
        print("\n❌ Google Photos test failed.")
        return False
        
    # Test 4: File operations
    if not test_file_operations(drive_manager):
        print("\n❌ File operations test failed.")
        return False
        
    print("\n" + "=" * 50)
    print("✅ All tests passed! The application should work correctly.")
    print("\nYou can now run the main application with:")
    print("   python main.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)