"""
Google Drive Manager
Handles all Google Drive API operations
"""

import io
import os
import logging
from pathlib import Path
from typing import Any

from googleapiclient.discovery import Resource
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError


class DriveManager:
    """Manages Google Drive operations through the Drive API"""
    
    def __init__(self, service: Resource):
        """Initialize the Drive Manager
        
        Args:
            service: Authenticated Google Drive API service resource
        """
        self.service = service
        
    def list_folders(self, parent_id: str = 'root') -> list[dict[str, Any]]:
        """List all folders in Google Drive
        
        Args:
            parent_id: ID of the parent folder to list contents of. Defaults to 'root'.
            
        Returns:
            List of folder dictionaries with 'id' and 'name'
        """
        try:
            logging.debug(f"Listing folders in parent_id: {parent_id}")
            results = self.service.files().list(
                q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name, parents)"
            ).execute()
            
            folders = results.get('files', [])
            logging.debug(f"Found {len(folders)} folders")
            return folders
            
        except HttpError as e:
            logging.error(f"Error listing folders: {e}")
            return []
            
    def get_folder_contents(self, folder_id: str, recursive: bool = True) -> list[dict[str, Any]]:
        """Get all files and subfolders in a Google Drive folder
        
        Args:
            folder_id: ID of the folder to get contents from
            recursive: Whether to include files from subfolders. Defaults to True.
            
        Returns:
            List of file/folder dictionaries
        """
        try:
            logging.debug(f"Getting contents of folder: {folder_id}, recursive={recursive}")
            files = []
            page_token = None
            
            while True:
                # Query for files in the folder (excluding Google Workspace files)
                query = (f"'{folder_id}' in parents and trashed=false and "
                        "mimeType!='application/vnd.google-apps.folder' and "
                        "mimeType!='application/vnd.google-apps.document' and "
                        "mimeType!='application/vnd.google-apps.spreadsheet' and "
                        "mimeType!='application/vnd.google-apps.presentation'")
                
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, size, createdTime, modifiedTime, mimeType, parents)",
                    pageToken=page_token,
                    pageSize=100  # Optimize by requesting maximum page size
                ).execute()
                
                batch_files = results.get('files', [])
                files.extend(batch_files)
                logging.debug(f"Retrieved {len(batch_files)} files from folder {folder_id}")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            # If recursive, also get files from subfolders
            if recursive:
                subfolders = self.list_folders(folder_id)
                for subfolder in subfolders:
                    subfolder_files = self.get_folder_contents(subfolder['id'], recursive=True)
                    files.extend(subfolder_files)
                    
            return files
            
        except HttpError as e:
            logging.error(f"Error getting folder contents: {e}")
            return []
            
    def download_file(self, file_id: str, local_path: str | Path) -> bool:
        """Download a file from Google Drive
        
        Args:
            file_id: ID of the file to download
            local_path: Path where the file should be saved
            
        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Ensure directory exists
            path = Path(local_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            logging.debug(f"Downloading file {file_id} to {local_path}")
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(local_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logging.debug(f"Download progress: {int(status.progress() * 100)}%")
                
            fh.close()
            logging.info(f"File {file_id} downloaded successfully to {local_path}")
            return True
            
        except HttpError as e:
            logging.error(f"Error downloading file: {e}")
            return False
            
    def upload_file(self, local_path: str | Path, filename: str, parent_folder_id: str) -> str | None:
        """Upload a file to Google Drive
        
        Args:
            local_path: Path to the local file to upload
            filename: Name to give the file in Google Drive
            parent_folder_id: ID of the folder to upload to
            
        Returns:
            File ID if successful, None otherwise
        """
        try:
            local_path_str = str(local_path)
            logging.debug(f"Uploading file {local_path_str} to folder {parent_folder_id} as {filename}")
            
            # Determine MIME type based on file extension
            mime_type = self._get_mime_type(local_path_str)
            
            file_metadata = {
                'name': filename,
                'parents': [parent_folder_id]
            }
            
            media = MediaFileUpload(local_path_str, mimetype=mime_type, resumable=True)
            
            result = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = result.get('id')
            logging.info(f"File {filename} uploaded successfully with ID: {file_id}")
            return file_id
            
        except HttpError as e:
            logging.error(f"Error uploading file: {e}")
            return None
            
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            logging.debug(f"Deleting file with ID: {file_id}")
            self.service.files().delete(fileId=file_id).execute()
            logging.info(f"File {file_id} deleted successfully")
            return True
        except HttpError as e:
            logging.error(f"Error deleting file: {e}")
            return False
            
    def get_file_info(self, file_id: str) -> dict[str, Any] | None:
        """Get detailed information about a file
        
        Args:
            file_id: ID of the file to get information for
            
        Returns:
            Dictionary with file information if successful, None otherwise
        """
        try:
            logging.debug(f"Getting info for file: {file_id}")
            result = self.service.files().get(
                fileId=file_id,
                fields="id, name, size, createdTime, modifiedTime, mimeType, parents, md5Checksum"
            ).execute()
            return result
        except HttpError as e:
            logging.error(f"Error getting file info: {e}")
            return None
            
    def _get_mime_type(self, file_path: str) -> str:
        """Determine MIME type based on file extension
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            '.m4v': 'video/x-m4v',
            '.3gp': 'video/3gpp',
            '.3g2': 'video/3gpp2',
            '.heic': 'image/heic',
            '.heif': 'image/heif'
        }
        
        mime_type = mime_types.get(extension, 'application/octet-stream')
        logging.debug(f"Determined MIME type for {extension}: {mime_type}")
        return mime_type
        
    def is_media_file(self, file_info: dict[str, Any]) -> bool:
        """Check if a file is a media file (image or video)
        
        Args:
            file_info: File information dictionary
            
        Returns:
            True if the file is a media file, False otherwise
        """
        mime_type = file_info.get('mimeType', '').lower()
        return mime_type.startswith('image/') or mime_type.startswith('video/')
        
    def create_folder(self, folder_name: str, parent_folder_id: str = 'root') -> str | None:
        """Create a new folder in Google Drive
        
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of the parent folder. Defaults to 'root'.
            
        Returns:
            Folder ID if successful, None otherwise
        """
        try:
            logging.debug(f"Creating folder {folder_name} in parent {parent_folder_id}")
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logging.info(f"Folder {folder_name} created successfully with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logging.error(f"Error creating folder: {e}")
            return None
            
    def search_files(self, query: str) -> list[dict[str, Any]]:
        """Search for files in Google Drive using a query
        
        Args:
            query: Search query in Drive query format
            
        Returns:
            List of file dictionaries matching the query
        """
        try:
            logging.debug(f"Searching files with query: {query}")
            files = []
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, size, createdTime, modifiedTime, mimeType, parents)",
                    pageToken=page_token,
                    pageSize=100
                ).execute()
                
                batch_files = results.get('files', [])
                files.extend(batch_files)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            logging.debug(f"Found {len(files)} files matching query")
            return files
            
        except HttpError as e:
            logging.error(f"Error searching files: {e}")
            return []