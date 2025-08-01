"""Tests for PhotosManager class."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
import requests

from photos_manager import PhotosManager


class TestPhotosManager(unittest.TestCase):
    """Test cases for PhotosManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        # Set up the mock chain for mediaItems
        self.mock_media_items = Mock()
        self.mock_service.mediaItems.return_value = self.mock_media_items
        
        # Set up individual method mocks
        self.mock_media_items.list.return_value = Mock()
        self.mock_media_items.search.return_value = Mock()
        self.mock_media_items.get.return_value = Mock()
        self.mock_media_items.batchCreate.return_value = Mock()
        
        self.photos_manager = PhotosManager(self.mock_service)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_all_media_items_success(self):
        """Test successful retrieval of all media items."""
        mock_items = [
            {'id': 'item1', 'filename': 'photo1.jpg'},
            {'id': 'item2', 'filename': 'photo2.jpg'}
        ]
        
        self.mock_media_items.list().execute.return_value = {
            'mediaItems': mock_items,
            'nextPageToken': None
        }
        
        result = self.photos_manager.get_all_media_items()
        
        self.assertEqual(result, mock_items)
        self.mock_media_items.list.assert_called_once()

    def test_get_all_media_items_with_pagination(self):
        """Test retrieval of media items with pagination."""
        first_page = [{'id': 'item1', 'filename': 'photo1.jpg'}]
        second_page = [{'id': 'item2', 'filename': 'photo2.jpg'}]
        
        self.mock_media_items.list().execute.side_effect = [
            {'mediaItems': first_page, 'nextPageToken': 'token123'},
            {'mediaItems': second_page, 'nextPageToken': None}
        ]
        
        result = self.photos_manager.get_all_media_items()
        
        expected = first_page + second_page
        self.assertEqual(result, expected)
        self.assertEqual(self.mock_media_items.list().execute.call_count, 2)

    def test_get_all_media_items_http_error(self):
        """Test media items retrieval with HTTP error."""
        self.mock_media_items.list().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        result = self.photos_manager.get_all_media_items()
        
        self.assertEqual(result, [])

    def test_search_media_items_success(self):
        """Test successful media items search."""
        mock_items = [
            {'id': 'item1', 'filename': 'vacation1.jpg'},
            {'id': 'item2', 'filename': 'vacation2.jpg'}
        ]
        
        filters = {'dateFilter': {'ranges': [{'startDate': {'year': 2023}}]}}
        
        self.mock_media_items.search().execute.return_value = {
            'mediaItems': mock_items,
            'nextPageToken': None
        }
        
        result = self.photos_manager.search_media_items(filters)
        
        self.assertEqual(result, mock_items)
        
        # Verify filters were passed
        call_args = self.mock_media_items.search.call_args
        self.assertEqual(call_args[1]['body']['filters'], filters)

    def test_search_media_items_no_filters(self):
        """Test media items search without filters."""
        mock_items = [{'id': 'item1', 'filename': 'photo.jpg'}]
        
        self.mock_media_items.search().execute.return_value = {
            'mediaItems': mock_items,
            'nextPageToken': None
        }
        
        result = self.photos_manager.search_media_items()
        
        self.assertEqual(result, mock_items)
        
        # Verify no filters were passed
        call_args = self.mock_media_items.search.call_args
        self.assertNotIn('filters', call_args[1]['body'])

    @patch('photos_manager.requests.get')
    def test_download_media_item_photo_success(self, mock_get):
        """Test successful photo download."""
        media_item = {
            'id': 'photo_id',
            'filename': 'photo.jpg',
            'baseUrl': 'https://example.com/photo',
            'mediaMetadata': {'photo': {}}
        }
        
        mock_response = Mock()
        mock_response.content = b'photo_data'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        test_path = Path(self.temp_dir) / 'downloaded_photo.jpg'
        
        result = self.photos_manager.download_media_item(media_item, test_path)
        
        self.assertTrue(result)
        self.assertTrue(test_path.exists())
        self.assertEqual(test_path.read_bytes(), b'photo_data')
        
        # Verify correct URL was used (photo download)
        mock_get.assert_called_once_with('https://example.com/photo=d', timeout=30)

    @patch('photos_manager.requests.get')
    def test_download_media_item_video_success(self, mock_get):
        """Test successful video download."""
        media_item = {
            'id': 'video_id',
            'filename': 'video.mp4',
            'baseUrl': 'https://example.com/video',
            'mediaMetadata': {'video': {}}
        }
        
        mock_response = Mock()
        mock_response.content = b'video_data'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        test_path = Path(self.temp_dir) / 'downloaded_video.mp4'
        
        result = self.photos_manager.download_media_item(media_item, test_path)
        
        self.assertTrue(result)
        self.assertTrue(test_path.exists())
        self.assertEqual(test_path.read_bytes(), b'video_data')
        
        # Verify correct URL was used (video download)
        mock_get.assert_called_once_with('https://example.com/video=dv', timeout=30)

    @patch('photos_manager.requests.get')
    def test_download_media_item_no_base_url(self, mock_get):
        """Test download failure when no baseUrl."""
        media_item = {
            'id': 'item_id',
            'filename': 'photo.jpg'
            # Missing baseUrl
        }
        
        test_path = Path(self.temp_dir) / 'photo.jpg'
        
        result = self.photos_manager.download_media_item(media_item, test_path)
        
        self.assertFalse(result)
        mock_get.assert_not_called()

    @patch('photos_manager.requests.get')
    def test_download_media_item_request_error(self, mock_get):
        """Test download failure with request error."""
        media_item = {
            'id': 'item_id',
            'filename': 'photo.jpg',
            'baseUrl': 'https://example.com/photo',
            'mediaMetadata': {'photo': {}}
        }
        
        mock_get.side_effect = requests.RequestException("Network error")
        
        test_path = Path(self.temp_dir) / 'photo.jpg'
        
        result = self.photos_manager.download_media_item(media_item, test_path)
        
        self.assertFalse(result)

    @patch('photos_manager.PhotosManager._upload_file_for_token')
    def test_upload_media_item_success(self, mock_upload_token):
        """Test successful media item upload."""
        mock_upload_token.return_value = 'upload_token_123'
        
        self.mock_media_items.batchCreate().execute.return_value = {
            'newMediaItemResults': [{
                'status': {'message': 'Success'},
                'mediaItem': {'id': 'new_item_id'}
            }]
        }
        
        # Create test file
        test_file = Path(self.temp_dir) / 'test_photo.jpg'
        test_file.write_bytes(b'test_photo_data')
        
        result = self.photos_manager.upload_media_item(
            test_file, 'uploaded_photo.jpg', 'Test description'
        )
        
        self.assertEqual(result, 'new_item_id')
        mock_upload_token.assert_called_once_with(test_file)
        
        # Verify batch create was called with correct parameters
        call_args = self.mock_media_items.batchCreate.call_args
        new_media_item = call_args[1]['body']['newMediaItems'][0]
        self.assertEqual(new_media_item['description'], 'Test description')
        self.assertEqual(new_media_item['simpleMediaItem']['uploadToken'], 'upload_token_123')
        self.assertEqual(new_media_item['simpleMediaItem']['fileName'], 'uploaded_photo.jpg')

    @patch('photos_manager.PhotosManager._upload_file_for_token')
    def test_upload_media_item_upload_token_failure(self, mock_upload_token):
        """Test upload failure when getting upload token fails."""
        mock_upload_token.return_value = None
        
        test_file = Path(self.temp_dir) / 'test_photo.jpg'
        test_file.write_bytes(b'test_photo_data')
        
        result = self.photos_manager.upload_media_item(test_file)
        
        self.assertIsNone(result)
        self.mock_media_items.batchCreate.assert_not_called()

    @patch('photos_manager.PhotosManager._upload_file_for_token')
    def test_upload_media_item_batch_create_failure(self, mock_upload_token):
        """Test upload failure when batch create fails."""
        mock_upload_token.return_value = 'upload_token_123'
        
        self.mock_media_items.batchCreate().execute.return_value = {
            'newMediaItemResults': [{
                'status': {'message': 'Error', 'code': 3}
            }]
        }
        
        test_file = Path(self.temp_dir) / 'test_photo.jpg'
        test_file.write_bytes(b'test_photo_data')
        
        result = self.photos_manager.upload_media_item(test_file)
        
        self.assertIsNone(result)

    @patch('photos_manager.requests.post')
    def test_upload_file_for_token_success(self, mock_post):
        """Test successful upload for token."""
        mock_response = Mock()
        mock_response.text = 'upload_token_123'
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Mock credentials
        self.mock_service._http.credentials.token = 'access_token_123'
        
        test_file = Path(self.temp_dir) / 'test_photo.jpg'
        test_file.write_bytes(b'test_photo_data')
        
        result = self.photos_manager._upload_file_for_token(test_file)
        
        self.assertEqual(result, 'upload_token_123')
        
        # Verify request was made with correct headers and data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        self.assertEqual(call_args[0][0], 'https://photoslibrary.googleapis.com/v1/uploads')
        self.assertEqual(call_args[1]['data'], b'test_photo_data')
        
        headers = call_args[1]['headers']
        self.assertEqual(headers['Authorization'], 'Bearer access_token_123')
        self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        self.assertEqual(headers['X-Goog-Upload-File-Name'], 'test_photo.jpg')

    @patch('photos_manager.requests.post')
    def test_upload_file_for_token_request_error(self, mock_post):
        """Test upload for token with request error."""
        mock_post.side_effect = requests.RequestException("Upload failed")
        
        self.mock_service._http.credentials.token = 'access_token_123'
        
        test_file = Path(self.temp_dir) / 'test_photo.jpg'
        test_file.write_bytes(b'test_photo_data')
        
        result = self.photos_manager._upload_file_for_token(test_file)
        
        self.assertIsNone(result)

    def test_get_media_item_info_success(self):
        """Test successful media item info retrieval."""
        mock_info = {
            'id': 'item_id',
            'filename': 'photo.jpg',
            'mediaMetadata': {'photo': {}}
        }
        
        self.mock_media_items.get().execute.return_value = mock_info
        
        result = self.photos_manager.get_media_item_info('item_id')
        
        self.assertEqual(result, mock_info)
        self.mock_media_items.get.assert_called_once_with(mediaItemId='item_id')

    def test_get_media_item_info_http_error(self):
        """Test media item info retrieval with HTTP error."""
        self.mock_media_items.get().execute.side_effect = HttpError(
            resp=Mock(status=404), content=b'Not Found'
        )
        
        result = self.photos_manager.get_media_item_info('item_id')
        
        self.assertIsNone(result)

    def test_create_album_success(self):
        """Test successful album creation."""
        self.mock_service.albums().create().execute.return_value = {
            'id': 'album_id_123'
        }
        
        result = self.photos_manager.create_album('My Album', 'Album description')
        
        self.assertEqual(result, 'album_id_123')
        
        # Verify correct parameters were passed
        call_args = self.mock_service.albums().create.call_args
        album_data = call_args[1]['body']['album']
        self.assertEqual(album_data['title'], 'My Album')
        self.assertEqual(album_data['description'], 'Album description')

    def test_create_album_http_error(self):
        """Test album creation with HTTP error."""
        self.mock_service.albums().create().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        result = self.photos_manager.create_album('My Album')
        
        self.assertIsNone(result)

    def test_add_media_to_album_success(self):
        """Test successful addition of media to album."""
        self.mock_service.albums().batchAddMediaItems().execute.return_value = None
        
        media_ids = ['item1', 'item2', 'item3']
        
        result = self.photos_manager.add_media_to_album('album_id', media_ids)
        
        self.assertTrue(result)
        
        # Verify correct parameters were passed
        call_args = self.mock_service.albums().batchAddMediaItems.call_args
        self.assertEqual(call_args[1]['albumId'], 'album_id')
        self.assertEqual(call_args[1]['body']['mediaItemIds'], media_ids)

    def test_add_media_to_album_http_error(self):
        """Test adding media to album with HTTP error."""
        self.mock_service.albums().batchAddMediaItems().execute.side_effect = HttpError(
            resp=Mock(status=400), content=b'Bad Request'
        )
        
        result = self.photos_manager.add_media_to_album('album_id', ['item1'])
        
        self.assertFalse(result)

    def test_parse_media_metadata_photo(self):
        """Test parsing metadata for photo."""
        media_item = {
            'id': 'photo_id',
            'filename': 'vacation.jpg',
            'description': 'Beach vacation',
            'mediaMetadata': {
                'creationTime': '2023-07-15T10:30:00Z',
                'width': '1920',
                'height': '1080',
                'photo': {
                    'cameraMake': 'Canon',
                    'cameraModel': 'EOS R5',
                    'focalLength': 85.0,
                    'apertureFNumber': 2.8,
                    'isoEquivalent': 200
                }
            },
            'mimeType': 'image/jpeg',
            'baseUrl': 'https://example.com/photo'
        }
        
        result = self.photos_manager.parse_media_metadata(media_item)
        
        expected = {
            'id': 'photo_id',
            'filename': 'vacation.jpg',
            'description': 'Beach vacation',
            'creation_time': '2023-07-15T10:30:00Z',
            'width': '1920',
            'height': '1080',
            'mime_type': 'image/jpeg',
            'base_url': 'https://example.com/photo',
            'is_video': False,
            'is_photo': True,
            'camera_make': 'Canon',
            'camera_model': 'EOS R5',
            'focal_length': 85.0,
            'aperture_f_number': 2.8,
            'iso_equivalent': 200
        }
        
        self.assertEqual(result, expected)

    def test_parse_media_metadata_video(self):
        """Test parsing metadata for video."""
        media_item = {
            'id': 'video_id',
            'filename': 'family_video.mp4',
            'mediaMetadata': {
                'creationTime': '2023-07-15T15:45:00Z',
                'width': '1920',
                'height': '1080',
                'video': {
                    'fps': 30.0,
                    'status': 'READY'
                }
            },
            'mimeType': 'video/mp4',
            'baseUrl': 'https://example.com/video'
        }
        
        result = self.photos_manager.parse_media_metadata(media_item)
        
        expected = {
            'id': 'video_id',
            'filename': 'family_video.mp4',
            'description': '',
            'creation_time': '2023-07-15T15:45:00Z',
            'width': '1920',
            'height': '1080',
            'mime_type': 'video/mp4',
            'base_url': 'https://example.com/video',
            'is_video': True,
            'is_photo': False,
            'fps': 30.0,
            'status': 'READY'
        }
        
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()