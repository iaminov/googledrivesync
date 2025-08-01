"""Integration tests for Google Drive & Photos Sync Application."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

from auth_manager import AuthManager
from drive_manager import DriveManager
from photos_manager import PhotosManager
from sync_engine import SyncEngine
from conflict_resolver import ConflictResolver


class TestIntegration(unittest.TestCase):
    """Integration test cases for the sync application."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.credentials_file = Path(self.temp_dir) / 'credentials.json'
        self.token_file = Path(self.temp_dir) / 'token.json'
        
        # Create mock credentials file
        self.credentials_file.write_text('''{
    "installed": {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}''')

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('auth_manager.build')
    @patch('auth_manager.InstalledAppFlow')
    @patch('auth_manager.Credentials')
    def test_full_authentication_flow(self, mock_credentials, mock_flow, mock_build):
        """Test complete authentication flow."""
        # Mock credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.refresh_token = 'refresh_token'
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        # Mock services
        mock_drive_service = Mock()
        mock_photos_service = Mock()
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        # Test authentication
        auth_manager = AuthManager(str(self.temp_dir))
        
        # Should authenticate successfully
        self.assertTrue(auth_manager.authenticate())
        self.assertTrue(auth_manager.is_authenticated())
        
        # Should get services
        drive_service = auth_manager.get_drive_service()
        photos_service = auth_manager.get_photos_service()
        
        self.assertIsNotNone(drive_service)
        self.assertIsNotNone(photos_service)

    @patch('auth_manager.build')
    @patch('auth_manager.InstalledAppFlow')
    @patch('auth_manager.Credentials')
    def test_managers_integration(self, mock_credentials, mock_flow, mock_build):
        """Test integration between managers."""
        # Setup authentication
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        mock_drive_service = Mock()
        mock_photos_service = Mock()
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        # Create managers
        auth_manager = AuthManager(str(self.temp_dir))
        auth_manager.authenticate()
        
        drive_manager = DriveManager(auth_manager.get_drive_service())
        photos_manager = PhotosManager(auth_manager.get_photos_service())
        
        # Test Drive manager operations
        mock_drive_service.files().list().execute.return_value = {
            'files': [
                {'id': 'folder1', 'name': 'Test Folder', 'mimeType': 'application/vnd.google-apps.folder'}
            ]
        }
        
        folders = drive_manager.list_folders()
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0]['name'], 'Test Folder')
        
        # Test Photos manager operations
        mock_photos_service.mediaItems().list().execute.return_value = {
            'mediaItems': [
                {'id': 'photo1', 'filename': 'test.jpg'}
            ]
        }
        
        media_items = photos_manager.get_all_media_items()
        self.assertEqual(len(media_items), 1)
        self.assertEqual(media_items[0]['filename'], 'test.jpg')

    @patch('auth_manager.build')
    @patch('auth_manager.InstalledAppFlow')
    @patch('auth_manager.Credentials')
    def test_sync_engine_integration(self, mock_credentials, mock_flow, mock_build):
        """Test sync engine integration with managers."""
        # Setup authentication and services
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        mock_drive_service = Mock()
        mock_photos_service = Mock()
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        # Create managers
        auth_manager = AuthManager(str(self.temp_dir))
        auth_manager.authenticate()
        
        drive_manager = DriveManager(auth_manager.get_drive_service())
        photos_manager = PhotosManager(auth_manager.get_photos_service())
        
        # Create conflict resolver and sync engine
        mock_parent = Mock()
        conflict_resolver = ConflictResolver(mock_parent)
        sync_engine = SyncEngine(drive_manager, photos_manager, conflict_resolver)
        
        # Test sync engine initialization
        self.assertFalse(sync_engine.is_syncing)
        self.assertIsNone(sync_engine.sync_thread)
        
        # Test starting sync
        with patch('sync_engine.threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            result = sync_engine.start_sync('folder_id', Path(self.temp_dir))
            
            self.assertTrue(result)
            self.assertTrue(sync_engine.is_syncing)
            mock_thread_instance.start.assert_called_once()

    @patch('auth_manager.build')
    @patch('auth_manager.InstalledAppFlow')
    @patch('auth_manager.Credentials')
    @patch('sync_engine.SyncEngine._perform_sync_operations')
    def test_end_to_end_sync_flow(self, mock_perform_sync, mock_credentials, mock_flow, mock_build):
        """Test end-to-end sync flow."""
        # Setup authentication
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        mock_drive_service = Mock()
        mock_photos_service = Mock()
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        # Create complete application stack
        auth_manager = AuthManager(str(self.temp_dir))
        auth_manager.authenticate()
        
        drive_manager = DriveManager(auth_manager.get_drive_service())
        photos_manager = PhotosManager(auth_manager.get_photos_service())
        
        mock_parent = Mock()
        conflict_resolver = ConflictResolver(mock_parent)
        sync_engine = SyncEngine(drive_manager, photos_manager, conflict_resolver)
        
        # Mock Drive folder contents
        mock_drive_service.files().list().execute.return_value = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'photo1.jpg',
                    'mimeType': 'image/jpeg',
                    'size': '1024',
                    'createdTime': '2023-07-15T10:30:00Z'
                }
            ],
            'nextPageToken': None
        }
        
        # Mock Photos media items
        mock_photos_service.mediaItems().list().execute.return_value = {
            'mediaItems': [
                {
                    'id': 'photo1',
                    'filename': 'photo2.jpg',
                    'creation_time': '2023-07-16T10:30:00Z',
                    'baseUrl': 'https://example.com/photo2'
                }
            ],
            'nextPageToken': None
        }
        
        # Start sync
        local_path = Path(self.temp_dir) / 'sync_folder'
        local_path.mkdir()
        
        with patch('sync_engine.threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            # Start sync
            result = sync_engine.start_sync('folder_id', local_path)
            self.assertTrue(result)
            
            # Simulate sync completion
            sync_engine._sync_worker('folder_id', local_path)
            
            # Verify sync was performed
            mock_perform_sync.assert_called_once_with('folder_id', local_path)

    def test_error_handling_integration(self):
        """Test error handling across components."""
        # Test with invalid credentials file
        invalid_creds_file = Path(self.temp_dir) / 'invalid.json'
        invalid_creds_file.write_text('invalid json')
        
        auth_manager = AuthManager(str(self.temp_dir))
        
        # Should handle invalid credentials gracefully
        result = auth_manager.authenticate()
        self.assertFalse(result)
        self.assertFalse(auth_manager.is_authenticated())

    @patch('auth_manager.build')
    @patch('auth_manager.InstalledAppFlow')
    @patch('auth_manager.Credentials')
    def test_service_error_handling(self, mock_credentials, mock_flow, mock_build):
        """Test service error handling."""
        # Setup authentication
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        # Mock service that raises errors
        mock_drive_service = Mock()
        mock_photos_service = Mock()
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        # Create managers
        auth_manager = AuthManager(str(self.temp_dir))
        auth_manager.authenticate()
        
        drive_manager = DriveManager(auth_manager.get_drive_service())
        photos_manager = PhotosManager(auth_manager.get_photos_service())
        
        # Test Drive service error
        from googleapiclient.errors import HttpError
        mock_drive_service.files().list().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        folders = drive_manager.list_folders()
        self.assertEqual(folders, [])  # Should return empty list on error
        
        # Test Photos service error
        mock_photos_service.mediaItems().list().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        media_items = photos_manager.get_all_media_items()
        self.assertEqual(media_items, [])  # Should return empty list on error

    @patch('auth_manager.build')
    @patch('auth_manager.InstalledAppFlow')
    @patch('auth_manager.Credentials')
    def test_file_operations_integration(self, mock_credentials, mock_flow, mock_build):
        """Test file operations integration."""
        # Setup authentication
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        mock_drive_service = Mock()
        mock_photos_service = Mock()
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        # Create managers
        auth_manager = AuthManager(str(self.temp_dir))
        auth_manager.authenticate()
        
        drive_manager = DriveManager(auth_manager.get_drive_service())
        photos_manager = PhotosManager(auth_manager.get_photos_service())
        
        # Test file type detection
        test_files = [
            {'name': 'photo.jpg', 'mimeType': 'image/jpeg'},
            {'name': 'video.mp4', 'mimeType': 'video/mp4'},
            {'name': 'document.pdf', 'mimeType': 'application/pdf'}
        ]
        
        for file_info in test_files:
            is_media = drive_manager.is_media_file(file_info)
            if file_info['mimeType'].startswith(('image/', 'video/')):
                self.assertTrue(is_media)
            else:
                self.assertFalse(is_media)

    def test_conflict_resolution_integration(self):
        """Test conflict resolution integration."""
        mock_parent = Mock()
        conflict_resolver = ConflictResolver(mock_parent)
        
        drive_file = {
            'name': 'photo.jpg',
            'size': '1024',
            'createdTime': '2023-07-15T10:30:00Z'
        }
        
        photos_item = {
            'filename': 'photo.jpg',
            'creation_time': '2023-07-16T10:30:00Z'
        }
        
        # Test that conflict resolver can be created and used
        self.assertIsNotNone(conflict_resolver)
        self.assertEqual(conflict_resolver.parent, mock_parent)
        
        # Test with mocked dialog
        with patch('conflict_resolver.tk.Toplevel') as mock_toplevel:
            mock_dialog = Mock()
            mock_toplevel.return_value = mock_dialog
            
            with patch.object(mock_dialog, 'wait_window'):
                
                conflict_resolver.result = 'same'
                result = conflict_resolver.resolve_conflict(drive_file, photos_item)
                
                self.assertEqual(result, 'same')

    @patch.dict(os.environ, {'GOOGLE_CLIENT_ID': 'test_id', 'GOOGLE_CLIENT_SECRET': 'test_secret'})
    def test_environment_variables_integration(self):
        """Test integration with environment variables."""
        # Test that environment variables can be accessed
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        self.assertEqual(client_id, 'test_id')
        self.assertEqual(client_secret, 'test_secret')
        
        # This tests the foundation for using environment variables
        # in the actual implementation

    def test_path_handling_integration(self):
        """Test path handling across components."""
        # Test various path scenarios
        test_paths = [
            Path(self.temp_dir) / 'sync_folder',
            Path(self.temp_dir) / 'nested' / 'folder',
            Path(self.temp_dir) / 'folder with spaces',
        ]
        
        for path in test_paths:
            # Create directory
            path.mkdir(parents=True, exist_ok=True)
            self.assertTrue(path.exists())
            self.assertTrue(path.is_dir())
            
            # Test file creation in directory
            test_file = path / 'test.txt'
            test_file.write_text('test content')
            self.assertTrue(test_file.exists())
            self.assertEqual(test_file.read_text(), 'test content')


if __name__ == '__main__':
    unittest.main()