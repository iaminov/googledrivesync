"""Tests for SyncEngine class."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from sync_engine import SyncEngine


class TestSyncEngine(unittest.TestCase):
    """Test cases for SyncEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_drive_manager = Mock()
        self.mock_photos_manager = Mock()
        self.mock_conflict_resolver = Mock()
        
        self.sync_engine = SyncEngine(
            self.mock_drive_manager,
            self.mock_photos_manager,
            self.mock_conflict_resolver,
            "test_folder_id"
        )
        
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test SyncEngine initialization."""
        self.assertEqual(self.sync_engine.drive_manager, self.mock_drive_manager)
        self.assertEqual(self.sync_engine.photos_manager, self.mock_photos_manager)
        self.assertEqual(self.sync_engine.conflict_resolver, self.mock_conflict_resolver)
        self.assertEqual(self.sync_engine.drive_folder_id, "test_folder_id")
        self.assertFalse(self.sync_engine.stop_requested)

    def test_start_sync_not_already_syncing(self):
        """Test starting sync normally."""
        with patch.object(self.sync_engine.drive_manager, 'get_folder_contents') as mock_get_drive:
            with patch.object(self.sync_engine.photos_manager, 'get_all_media_items') as mock_get_photos:
                mock_get_drive.return_value = []
                mock_get_photos.return_value = []
                
                self.sync_engine.start_sync()
                
                mock_get_drive.assert_called_once()
                mock_get_photos.assert_called_once()

    def test_start_sync_already_syncing(self):
        """Test starting sync when stop is requested."""
        self.sync_engine.stop_requested = True
        
        with patch.object(self.sync_engine.drive_manager, 'get_folder_contents') as mock_drive, \
             patch.object(self.sync_engine.photos_manager, 'get_all_media_items') as mock_photos:
            mock_drive.return_value = []
            mock_photos.return_value = []
            
            self.sync_engine.start_sync()
            
            # Should still call get_folder_contents
            mock_drive.assert_called_once()

    def test_stop_sync_when_syncing(self):
        """Test stopping sync."""
        self.sync_engine.stop_sync()
        
        self.assertTrue(self.sync_engine.stop_requested)

    def test_stop_sync_when_not_syncing(self):
        """Test stopping sync when not currently syncing."""
        # Should not raise any exception
        self.sync_engine.stop_sync()
        
        self.assertTrue(self.sync_engine.stop_requested)

    def test_sync_worker_success(self):
        """Test successful sync execution."""
        with patch.object(self.sync_engine.drive_manager, 'get_folder_contents') as mock_get_drive:
            with patch.object(self.sync_engine.photos_manager, 'get_all_media_items') as mock_get_photos:
                with patch.object(self.sync_engine, '_perform_sync_operations') as mock_perform:
                    mock_get_drive.return_value = []
                    mock_get_photos.return_value = []
                    mock_perform.return_value = None
                    
                    self.sync_engine.start_sync()
                    
                    mock_get_drive.assert_called_once()
                    mock_get_photos.assert_called_once()

    def test_sync_worker_exception(self):
        """Test sync exception handling."""
        with patch.object(self.sync_engine.drive_manager, 'get_folder_contents') as mock_get:
            mock_get.side_effect = Exception("Test error")
            
            with self.assertRaises(Exception):
                self.sync_engine.start_sync()

    def test_compare_files_identical(self):
        """Test comparing identical files."""
        drive_files = [{
            'id': '1',
            'name': 'photo.jpg',
            'size': '1024',
            'createdTime': '2023-07-15T10:30:00Z'
        }]
        photos_metadata = [{
            'id': 'p1',
            'filename': 'photo.jpg',
            'creation_time': '2023-07-15T10:30:00Z'
        }]
        
        result = self.sync_engine._compare_files(drive_files, photos_metadata)
        
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(len(result['drive_only']), 0)
        self.assertEqual(len(result['photos_only']), 0)
        self.assertEqual(len(result['conflicts']), 0)

    def test_compare_files_different_names(self):
        """Test comparing files with different names."""
        drive_files = [{
            'id': '1',
            'name': 'photo1.jpg',
            'size': '1024',
            'createdTime': '2023-07-15T10:30:00Z'
        }]
        photos_metadata = [{
            'id': 'p1',
            'filename': 'photo2.jpg',
            'creation_time': '2023-07-15T10:30:00Z'
        }]
        
        result = self.sync_engine._compare_files(drive_files, photos_metadata)
        
        self.assertEqual(len(result['matches']), 0)
        self.assertEqual(len(result['drive_only']), 1)
        self.assertEqual(len(result['photos_only']), 1)
        self.assertEqual(len(result['conflicts']), 0)

    def test_compare_files_different_dates(self):
        """Test comparing files with different dates."""
        drive_files = [{
            'id': '1',
            'name': 'photo.jpg',
            'size': '1024',
            'createdTime': '2023-07-15T10:30:00Z'
        }]
        photos_metadata = [{
            'id': 'p1',
            'filename': 'photo.jpg',
            'creation_time': '2023-07-17T10:30:00Z'  # Different date (more than 24h)
        }]
        
        result = self.sync_engine._compare_files(drive_files, photos_metadata)
        
        self.assertEqual(len(result['matches']), 0)
        self.assertEqual(len(result['drive_only']), 0)
        self.assertEqual(len(result['photos_only']), 0)
        self.assertEqual(len(result['conflicts']), 1)

    def test_compare_files_missing_data(self):
        """Test comparing files with missing data."""
        drive_files = [{
            'id': '1',
            'name': 'photo.jpg',
            'size': '1024'
            # Missing createdTime
        }]
        photos_metadata = [{
            'id': 'p1',
            'filename': 'photo.jpg',
            'creation_time': '2023-07-15T10:30:00Z'
        }]
        
        result = self.sync_engine._compare_files(drive_files, photos_metadata)
        
        # Should be treated as conflict due to missing date info
        self.assertEqual(len(result['matches']), 0)
        self.assertEqual(len(result['conflicts']), 1)











    def test_perform_sync_operations_drive_only_files(self):
        """Test syncing files that exist only in Drive."""
        comparison_result = {
            'drive_only': [
                {
                    'id': 'file1',
                    'name': 'photo1.jpg',
                    'mimeType': 'image/jpeg',
                    'size': '1024',
                    'createdTime': '2023-07-15T10:30:00Z'
                }
            ],
            'photos_only': [],
            'matches': [],
            'conflicts': []
        }
        
        # Mock successful download and upload
        self.mock_drive_manager.download_file.return_value = True
        self.mock_photos_manager.upload_media_item.return_value = 'new_item_id'
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Verify file was processed
        self.mock_drive_manager.download_file.assert_called_once()
        self.mock_photos_manager.upload_media_item.assert_called_once()

    def test_perform_sync_operations_matches(self):
        """Test syncing when files match between Drive and Photos."""
        comparison_result = {
            'drive_only': [],
            'photos_only': [],
            'matches': [
                {
                    'drive_file': {
                        'id': 'file1',
                        'name': 'photo1.jpg',
                        'mimeType': 'image/jpeg',
                        'size': '1024',
                        'createdTime': '2023-07-15T10:30:00Z'
                    },
                    'photos_item': {
                        'id': 'photo_item1',
                        'filename': 'photo1.jpg',
                        'creation_time': '2023-07-15T10:30:00Z'
                    }
                }
            ],
            'conflicts': []
        }
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Should not download or upload for matches
        self.mock_drive_manager.download_file.assert_not_called()
        self.mock_photos_manager.upload_media_item.assert_not_called()
        self.mock_photos_manager.download_media_item.assert_not_called()
        self.mock_drive_manager.upload_file.assert_not_called()

    def test_perform_sync_operations_conflicts_resolved_same(self):
        """Test syncing with conflict resolved as same file."""
        comparison_result = {
            'drive_only': [],
            'photos_only': [],
            'matches': [],
            'conflicts': [
                {
                    'drive_file': {
                        'id': 'file1',
                        'name': 'photo1.jpg',
                        'mimeType': 'image/jpeg',
                        'size': '1024',
                        'createdTime': '2023-07-15T10:30:00Z'
                    },
                    'photos_item': {
                        'id': 'photo_item1',
                        'filename': 'photo1.jpg',
                        'creation_time': '2023-07-16T10:30:00Z'
                    }
                }
            ]
        }
        
        # Mock conflict resolution
        self.mock_conflict_resolver.resolve_conflict.return_value = 'same'
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Should not download or upload when resolved as same
        self.mock_drive_manager.download_file.assert_not_called()
        self.mock_photos_manager.upload_media_item.assert_not_called()
        self.mock_photos_manager.download_media_item.assert_not_called()
        self.mock_drive_manager.upload_file.assert_not_called()

    def test_perform_sync_operations_download_failure(self):
        """Test syncing when download fails."""
        comparison_result = {
            'drive_only': [
                {
                    'id': 'file1',
                    'name': 'photo1.jpg',
                    'mimeType': 'image/jpeg',
                    'size': '1024',
                    'createdTime': '2023-07-15T10:30:00Z'
                }
            ],
            'photos_only': [],
            'matches': [],
            'conflicts': []
        }
        
        # Mock failed download
        self.mock_drive_manager.download_file.return_value = False
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Should not attempt upload when download fails
        self.mock_photos_manager.upload_media_item.assert_not_called()

    def test_perform_sync_operations_photos_only_files(self):
        """Test syncing files that exist only in Photos."""
        comparison_result = {
            'drive_only': [],
            'photos_only': [
                {
                    'id': 'photo1',
                    'filename': 'vacation1.jpg',
                    'creation_time': '2023-07-15T10:30:00Z',
                    'baseUrl': 'https://example.com/photo1'
                },
                {
                    'id': 'photo2',
                    'filename': 'vacation2.jpg',
                    'creation_time': '2023-07-15T11:00:00Z',
                    'baseUrl': 'https://example.com/photo2'
                }
            ],
            'matches': [],
            'conflicts': []
        }
        
        # Mock successful download and upload
        self.mock_photos_manager.download_media_item.return_value = True
        self.mock_drive_manager.upload_file.return_value = 'new_file_id'
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Verify both files were processed
        self.assertEqual(self.mock_photos_manager.download_media_item.call_count, 2)
        self.assertEqual(self.mock_drive_manager.upload_file.call_count, 2)

    def test_perform_sync_operations_no_actions_needed(self):
        """Test syncing when no actions are needed."""
        comparison_result = {
            'drive_only': [],
            'photos_only': [],
            'matches': [
                {
                    'drive_file': {
                        'id': 'file1',
                        'name': 'vacation1.jpg',
                        'size': '1024',
                        'createdTime': '2023-07-15T10:30:00Z'
                    },
                    'photos_item': {
                        'id': 'photo1',
                        'filename': 'vacation1.jpg',
                        'creation_time': '2023-07-15T10:30:00Z',
                        'baseUrl': 'https://example.com/photo1'
                    }
                }
            ],
            'conflicts': []
        }
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Should not download or upload for matches
        self.mock_photos_manager.download_media_item.assert_not_called()
        self.mock_drive_manager.upload_file.assert_not_called()
        self.mock_drive_manager.download_file.assert_not_called()
        self.mock_photos_manager.upload_media_item.assert_not_called()

    def test_perform_sync_operations_photos_download_failure(self):
        """Test syncing when download from Photos fails."""
        comparison_result = {
            'drive_only': [],
            'photos_only': [
                {
                    'id': 'photo1',
                    'filename': 'vacation1.jpg',
                    'creation_time': '2023-07-15T10:30:00Z',
                    'baseUrl': 'https://example.com/photo1'
                }
            ],
            'matches': [],
            'conflicts': []
        }
        
        # Mock failed download
        self.mock_photos_manager.download_media_item.return_value = False
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Should not attempt upload when download fails
        self.mock_drive_manager.upload_file.assert_not_called()

    def test_perform_sync_operations_photos_no_base_url(self):
        """Test syncing when Photos item has no baseUrl."""
        comparison_result = {
            'drive_only': [],
            'photos_only': [
                {
                    'id': 'photo1',
                    'filename': 'vacation1.jpg',
                    'creation_time': '2023-07-15T10:30:00Z'
                    # Missing baseUrl
                }
            ],
            'matches': [],
            'conflicts': []
        }
        
        self.sync_engine._perform_sync_operations(comparison_result)
        
        # Should not attempt download or upload when baseUrl is missing
        self.mock_photos_manager.download_media_item.assert_not_called()
        self.mock_drive_manager.upload_file.assert_not_called()


if __name__ == '__main__':
    unittest.main()