"""
Google Photos Manager
Handles all Google Photos API operations
"""

import io
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict, NotRequired

import requests
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError


class MediaMetadata(TypedDict):
    """Type definition for media item metadata"""
    id: str
    filename: str
    creation_time: str
    mime_type: str
    width: NotRequired[int]
    height: NotRequired[int]
    is_photo: bool
    is_video: bool
    camera_make: NotRequired[str]
    camera_model: NotRequired[str]
    fps: NotRequired[float]
    status: NotRequired[str]


class PhotosManager:
    """Manages Google Photos operations through the Photos API"""
    
    def __init__(self, service: Resource):
        """Initialize the Photos Manager
        
        Args:
            service: Authenticated Google Photos API service resource
        """
        self.service = service
        
    def get_all_media_items(self) -> list[dict[str, Any]]:
        """Get all media items from Google Photos
        
        Returns:
            List of media item dictionaries
        """
        try:
            logging.debug("Fetching all media items from Google Photos")
            media_items = []
            page_token = None
            
            while True:
                request_body = {
                    'pageSize': 100  # Maximum allowed by the API
                }
                
                if page_token:
                    request_body['pageToken'] = page_token
                    
                results = self.service.mediaItems().list(
                    body=request_body
                ).execute()
                
                batch_items = results.get('mediaItems', [])
                media_items.extend(batch_items)
                logging.debug(f"Retrieved {len(batch_items)} media items")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            logging.info(f"Retrieved a total of {len(media_items)} media items")
            return media_items
            
        except HttpError as e:
            logging.error(f"Error getting media items: {e}")
            return []
            
    def search_media_items(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search media items with optional filters
        
        Args:
            filters: Optional filters to apply to the search
            
        Returns:
            List of media item dictionaries matching the filters
        """
        try:
            filter_desc = "with filters" if filters else "without filters"
            logging.debug(f"Searching media items {filter_desc}")
            
            media_items = []
            page_token = None
            
            while True:
                request_body = {
                    'pageSize': 100  # Maximum allowed by the API
                }
                
                if filters:
                    request_body['filters'] = filters
                    
                if page_token:
                    request_body['pageToken'] = page_token
                    
                results = self.service.mediaItems().search(
                    body=request_body
                ).execute()
                
                batch_items = results.get('mediaItems', [])
                media_items.extend(batch_items)
                logging.debug(f"Retrieved {len(batch_items)} media items in search batch")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            logging.info(f"Search returned {len(media_items)} media items")
            return media_items
            
        except HttpError as e:
            logging.error(f"Error searching media items: {e}")
            return []
            
    def download_media_item(self, media_item: dict[str, Any], local_path: str | Path) -> bool:
        """Download a media item from Google Photos
        
        Args:
            media_item: Media item dictionary from the Photos API
            local_path: Path where the file should be saved
            
        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Ensure directory exists
            path = Path(local_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get media item details for logging
            item_id = media_item.get('id', 'unknown')
            filename = media_item.get('filename', 'unknown')
            logging.debug(f"Downloading media item {item_id} ({filename}) to {local_path}")
            
            # Get the base URL for download
            base_url = media_item.get('baseUrl')
            if not base_url:
                logging.error(f"No baseUrl found for media item {item_id}")
                return False
                
            # Add download parameters
            if media_item.get('mediaMetadata', {}).get('video'):
                # For videos, add video download parameter
                download_url = f"{base_url}=dv"
                logging.debug(f"Using video download URL for {item_id}")
            else:
                # For photos, add high quality download parameter
                download_url = f"{base_url}=d"
                logging.debug(f"Using photo download URL for {item_id}")
                
            # Download the file
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
                
            logging.info(f"Media item {item_id} downloaded successfully to {local_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error downloading media item: {e}")
            return False
            
    def upload_media_item(self, local_path: str | Path, filename: str | None = None, description: str | None = None) -> str | None:
        """Upload a media item to Google Photos
        
        Args:
            local_path: Path to the local file to upload
            filename: Optional filename to use. If None, uses the basename of local_path
            description: Optional description for the media item
            
        Returns:
            Media item ID if successful, None otherwise
        """
        try:
            path = Path(local_path)
            if not filename:
                filename = path.name
                
            logging.debug(f"Uploading media item {local_path} as {filename}")
            
            # Step 1: Upload the file to get an upload token
            upload_token = self._upload_file_for_token(local_path)
            if not upload_token:
                logging.error(f"Failed to get upload token for {local_path}")
                return None
                
            logging.debug(f"Received upload token for {filename}")
                
            # Step 2: Create the media item
            new_media_item = {
                'description': description or filename,
                'simpleMediaItem': {
                    'uploadToken': upload_token,
                    'fileName': filename
                }
            }
            
            request_body = {
                'newMediaItems': [new_media_item]
            }
            
            logging.debug(f"Creating media item with upload token")
            result = self.service.mediaItems().batchCreate(
                body=request_body
            ).execute()
            
            new_media_items = result.get('newMediaItemResults', [])
            if new_media_items and new_media_items[0].get('status', {}).get('message') == 'Success':
                media_item_id = new_media_items[0].get('mediaItem', {}).get('id')
                logging.info(f"Media item {filename} uploaded successfully with ID: {media_item_id}")
                return media_item_id
            else:
                status = new_media_items[0].get('status', {}) if new_media_items else 'Unknown error'
                logging.error(f"Upload failed: {status}")
                return None
                
        except HttpError as e:
            logging.error(f"Error uploading media item: {e}")
            return None
            
    def _upload_file_for_token(self, local_path: str | Path) -> str | None:
        """Upload a file to get an upload token
        This is the first step in the upload process
        
        Args:
            local_path: Path to the local file to upload
            
        Returns:
            Upload token if successful, None otherwise
        """
        try:
            path = Path(local_path)
            file_size = path.stat().st_size
            logging.debug(f"Uploading file for token: {path.name} ({file_size} bytes)")
            
            # Read the file
            with open(local_path, 'rb') as f:
                file_content = f.read()
                
            # Get upload URL
            upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
            
            # Prepare headers
            headers = {
                'Authorization': f'Bearer {self.service._http.credentials.token}',
                'Content-Type': 'application/octet-stream',
                'X-Goog-Upload-File-Name': os.path.basename(str(local_path)),
                'X-Goog-Upload-Protocol': 'raw'
            }
            
            # Upload the file
            logging.debug(f"Sending upload request for {path.name}")
            response = requests.post(upload_url, headers=headers, data=file_content, timeout=60)
            response.raise_for_status()
            
            # The response body is the upload token
            token = response.text
            logging.debug(f"Received upload token for {path.name}")
            return token
            
        except Exception as e:
            logging.error(f"Error uploading file for token: {e}")
            return None
            
    def get_media_item_info(self, media_item_id: str) -> dict[str, Any] | None:
        """Get detailed information about a media item
        
        Args:
            media_item_id: ID of the media item to get information for
            
        Returns:
            Dictionary with media item information if successful, None otherwise
        """
        try:
            logging.debug(f"Getting info for media item: {media_item_id}")
            result = self.service.mediaItems().get(
                mediaItemId=media_item_id
            ).execute()
            return result
        except HttpError as e:
            logging.error(f"Error getting media item info: {e}")
            return None
            
    def create_album(self, title: str, description: str | None = None) -> str | None:
        """Create a new album in Google Photos
        
        Args:
            title: Title of the album
            description: Optional description for the album
            
        Returns:
            Album ID if successful, None otherwise
        """
        try:
            logging.debug(f"Creating album: {title}")
            
            request_body = {
                'album': {
                    'title': title
                }
            }
            
            if description:
                request_body['album']['description'] = description
                
            result = self.service.albums().create(
                body=request_body
            ).execute()
            
            album_id = result.get('id')
            if album_id:
                logging.info(f"Album {title} created successfully with ID: {album_id}")
            else:
                logging.error(f"Failed to create album {title}")
                
            return album_id
            
        except HttpError as e:
            logging.error(f"Error creating album: {e}")
            return None
            
    def add_media_to_album(self, album_id: str, media_item_ids: list[str]) -> bool:
        """Add media items to an album
        
        Args:
            album_id: ID of the album to add media to
            media_item_ids: List of media item IDs to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logging.debug(f"Adding {len(media_item_ids)} media items to album {album_id}")
            
            request_body = {
                'mediaItemIds': media_item_ids
            }
            
            self.service.albums().batchAddMediaItems(
                albumId=album_id,
                body=request_body
            ).execute()
            
            logging.info(f"Added {len(media_item_ids)} media items to album {album_id}")
            return True
            
        except HttpError as e:
            logging.error(f"Error adding media to album: {e}")
            return False
            
    def parse_media_metadata(self, media_item):
        """
        Parse media metadata from a media item
        Returns a dictionary with useful metadata
        """
        metadata = {
            'id': media_item.get('id'),
            'filename': media_item.get('filename'),
            'description': media_item.get('description', ''),
            'creation_time': media_item.get('mediaMetadata', {}).get('creationTime'),
            'width': media_item.get('mediaMetadata', {}).get('width'),
            'height': media_item.get('mediaMetadata', {}).get('height'),
            'mime_type': media_item.get('mimeType'),
            'base_url': media_item.get('baseUrl'),
            'is_video': 'video' in media_item.get('mediaMetadata', {}),
            'is_photo': 'photo' in media_item.get('mediaMetadata', {})
        }
        
        # Add video-specific metadata
        if metadata['is_video']:
            video_metadata = media_item.get('mediaMetadata', {}).get('video', {})
            metadata['fps'] = video_metadata.get('fps')
            metadata['status'] = video_metadata.get('status')
            
        # Add photo-specific metadata
        if metadata['is_photo']:
            photo_metadata = media_item.get('mediaMetadata', {}).get('photo', {})
            metadata['camera_make'] = photo_metadata.get('cameraMake')
            metadata['camera_model'] = photo_metadata.get('cameraModel')
            metadata['focal_length'] = photo_metadata.get('focalLength')
            metadata['aperture_f_number'] = photo_metadata.get('apertureFNumber')
            metadata['iso_equivalent'] = photo_metadata.get('isoEquivalent')
            metadata['exposure_time'] = photo_metadata.get('exposureTime')
            
        return metadata