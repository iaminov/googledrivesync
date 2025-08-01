"""Tests for DriveManager class."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from drive_manager import DriveManager


class TestDriveManager(unittest.TestCase):
    """Test cases for DriveManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        # Set up the mock chain for files
        self.mock_files = Mock()
        self.mock_service.files.return_value = self.mock_files
        
        # Set up individual method mocks
        self.mock_files.list.return_value = Mock()
        self.mock_files.create.return_value = Mock()
        self.mock_files.get.return_value = Mock()
        self.mock_files.get_media.return_value = Mock()
        self.mock_files.delete.return_value = Mock()
        
        self.drive_manager = DriveManager(self.mock_service)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_folders_success(self):
        """Test successful folder listing."""
        mock_folders = [
            {'id': 'folder1', 'name': 'Folder 1'},
            {'id': 'folder2', 'name': 'Folder 2'}
        ]
        
        self.mock_files.list().execute.return_value = {
            'files': mock_folders
        }
        
        result = self.drive_manager.list_folders()
        
        self.assertEqual(result, mock_folders)
        self.mock_files.list.assert_called_once()

    def test_list_folders_http_error(self):
        """Test folder listing with HTTP error."""
        self.mock_files.list().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        result = self.drive_manager.list_folders()
        
        self.assertEqual(result, [])

    def test_get_folder_contents_non_recursive(self):
        """Test getting folder contents without recursion."""
        mock_files = [
            {'id': 'file1', 'name': 'image.jpg', 'mimeType': 'image/jpeg'},
            {'id': 'file2', 'name': 'video.mp4', 'mimeType': 'video/mp4'}
        ]
        
        self.mock_files.list().execute.return_value = {
            'files': mock_files,
            'nextPageToken': None
        }
        
        result = self.drive_manager.get_folder_contents('folder_id', recursive=False)
        
        self.assertEqual(result, mock_files)

    def test_get_folder_contents_with_pagination(self):
        """Test getting folder contents with pagination."""
        # First page
        first_page = [{'id': 'file1', 'name': 'image1.jpg'}]
        # Second page
        second_page = [{'id': 'file2', 'name': 'image2.jpg'}]
        
        self.mock_files.list().execute.side_effect = [
            {'files': first_page, 'nextPageToken': 'token123'},
            {'files': second_page, 'nextPageToken': None}
        ]
        
        result = self.drive_manager.get_folder_contents('folder_id', recursive=False)
        
        expected = first_page + second_page
        self.assertEqual(result, expected)
        self.assertEqual(self.mock_files.list().execute.call_count, 2)

    @patch('drive_manager.MediaIoBaseDownload')
    @patch('builtins.open', create=True)
    def test_download_file_success(self, mock_open, mock_downloader_class):
        """Test successful file download."""
        mock_downloader = Mock()
        mock_downloader.next_chunk.side_effect = [
            (Mock(progress=lambda: 0.5), False),
            (Mock(progress=lambda: 1.0), True)
        ]
        mock_downloader_class.return_value = mock_downloader
        
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        self.mock_files.get_media.return_value = Mock()
        
        result = self.drive_manager.download_file('file_id', '/path/to/file.jpg')
        
        self.assertTrue(result)
        self.mock_files.get_media.assert_called_once_with(fileId='file_id')

    def test_download_file_http_error(self):
        """Test file download with HTTP error."""
        self.mock_files.get_media.side_effect = HttpError(
            resp=Mock(status=404), content=b'Not Found'
        )
        
        result = self.drive_manager.download_file('file_id', '/path/to/file.jpg')
        
        self.assertFalse(result)

    @patch('drive_manager.MediaFileUpload')
    def test_upload_file_success(self, mock_media_upload):
        """Test successful file upload."""
        mock_upload = Mock()
        mock_media_upload.return_value = mock_upload
        
        self.mock_files.create().execute.return_value = {
            'id': 'new_file_id'
        }
        
        # Create a temporary file
        test_file = Path(self.temp_dir) / 'test.jpg'
        test_file.write_bytes(b'test image data')
        
        result = self.drive_manager.upload_file(
            test_file, 'uploaded_image.jpg', 'parent_folder_id'
        )
        
        self.assertEqual(result, 'new_file_id')
        self.mock_files.create.assert_called_once()

    def test_upload_file_http_error(self):
        """Test file upload with HTTP error."""
        self.mock_files.create().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        # Create a temporary file
        test_file = Path(self.temp_dir) / 'test.jpg'
        test_file.write_bytes(b'test image data')
        
        result = self.drive_manager.upload_file(
            test_file, 'uploaded_image.jpg', 'parent_folder_id'
        )
        
        self.assertIsNone(result)

    def test_delete_file_success(self):
        """Test successful file deletion."""
        self.mock_files.delete().execute.return_value = None
        
        result = self.drive_manager.delete_file('file_id')
        
        self.assertTrue(result)
        self.mock_files.delete.assert_called_once_with(fileId='file_id')

    def test_delete_file_http_error(self):
        """Test file deletion with HTTP error."""
        self.mock_files.delete().execute.side_effect = HttpError(
            resp=Mock(status=404), content=b'Not Found'
        )
        
        result = self.drive_manager.delete_file('file_id')
        
        self.assertFalse(result)

    def test_get_file_info_success(self):
        """Test successful file info retrieval."""
        mock_file_info = {
            'id': 'file_id',
            'name': 'test.jpg',
            'size': '1024',
            'mimeType': 'image/jpeg'
        }
        
        self.mock_files.get().execute.return_value = mock_file_info
        
        result = self.drive_manager.get_file_info('file_id')
        
        self.assertEqual(result, mock_file_info)

    def test_get_file_info_http_error(self):
        """Test file info retrieval with HTTP error."""
        self.mock_files.get().execute.side_effect = HttpError(
            resp=Mock(status=404), content=b'Not Found'
        )
        
        result = self.drive_manager.get_file_info('file_id')
        
        self.assertIsNone(result)

    def test_get_mime_type(self):
        """Test MIME type determination."""
        test_cases = [
            ('image.jpg', 'image/jpeg'),
            ('video.mp4', 'video/mp4'),
            ('document.pdf', 'application/octet-stream'),
            ('photo.JPEG', 'image/jpeg'),  # Test case insensitive
        ]
        
        for filename, expected_mime in test_cases:
            with self.subTest(filename=filename):
                result = self.drive_manager._get_mime_type(filename)
                self.assertEqual(result, expected_mime)

    def test_is_media_file(self):
        """Test media file detection."""
        test_cases = [
            ({'mimeType': 'image/jpeg'}, True),
            ({'mimeType': 'video/mp4'}, True),
            ({'mimeType': 'application/pdf'}, False),
            ({'mimeType': 'text/plain'}, False),
        ]
        
        for file_info, expected in test_cases:
            with self.subTest(mime_type=file_info['mimeType']):
                result = self.drive_manager.is_media_file(file_info)
                self.assertEqual(result, expected)

    def test_create_folder_success(self):
        """Test successful folder creation."""
        self.mock_files.create().execute.return_value = {
            'id': 'new_folder_id'
        }
        
        result = self.drive_manager.create_folder('New Folder', 'parent_id')
        
        self.assertEqual(result, 'new_folder_id')
        
        # Verify the correct metadata was sent
        call_args = self.mock_files.create.call_args
        body = call_args[1]['body']
        self.assertEqual(body['name'], 'New Folder')
        self.assertEqual(body['mimeType'], 'application/vnd.google-apps.folder')
        self.assertEqual(body['parents'], ['parent_id'])

    def test_create_folder_http_error(self):
        """Test folder creation with HTTP error."""
        self.mock_files.create().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        result = self.drive_manager.create_folder('New Folder')
        
        self.assertIsNone(result)

    def test_search_files_success(self):
        """Test successful file search."""
        mock_files = [
            {'id': 'file1', 'name': 'image1.jpg'},
            {'id': 'file2', 'name': 'image2.jpg'}
        ]
        
        self.mock_files.list().execute.return_value = {
            'files': mock_files,
            'nextPageToken': None
        }
        
        result = self.drive_manager.search_files("name contains 'image'")
        
        self.assertEqual(result, mock_files)
        
        # Verify the query was passed correctly
        call_args = self.mock_files.list.call_args
        self.assertEqual(call_args[1]['q'], "name contains 'image'")

    def test_search_files_http_error(self):
        """Test file search with HTTP error."""
        self.mock_files.list().execute.side_effect = HttpError(
            resp=Mock(status=400), content=b'Bad Request'
        )
        
        result = self.drive_manager.search_files("invalid query")
        
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()