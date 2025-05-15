"""Sync Engine - Main synchronization logic between Google Drive and Google Photos"""

import hashlib
import logging
import os
import tempfile
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable

from drive_manager import DriveManager
from photos_manager import PhotosManager
from conflict_resolver import ConflictResolver, ConflictResolution


class SyncResult(Enum):
    """Enum representing possible sync operation results"""
    SUCCESS = auto()
    FAILURE = auto()
    SKIPPED = auto()
    CONFLICT = auto()


class SyncEngine:
    """Main synchronization engine between Google Drive and Google Photos"""
    
    def __init__(self, drive_manager: DriveManager, photos_manager: PhotosManager, 
                 conflict_resolver: ConflictResolver, drive_folder_id: str):
        """Initialize the sync engine
        
        Args:
            drive_manager: Google Drive manager instance
            photos_manager: Google Photos manager instance
            conflict_resolver: Conflict resolver instance
            drive_folder_id: ID of the Google Drive folder to sync
        """
        self.drive_manager = drive_manager
        self.photos_manager = photos_manager
        self.conflict_resolver = conflict_resolver
        self.drive_folder_id = drive_folder_id
        self.stop_requested = False
        
        self.stats = {
            'drive_to_photos_uploads': 0,
            'photos_to_drive_downloads': 0,
            'conflicts_resolved': 0,
            'errors': 0
        }
        
    def start_sync(self, progress_callback: Callable[[int], None] | None = None, 
                 status_callback: Callable[[str], None] | None = None, 
                 log_callback: Callable[[str], None] | None = None) -> None:
        """Start the synchronization process between Google Drive and Google Photos
        
        Args:
            progress_callback: Callback function to report progress percentage (0-100)
            status_callback: Callback function to report current status message
            log_callback: Callback function to report detailed log messages
        """
        self.stop_requested = False
        self.stats = {
            'drive_to_photos_uploads': 0,
            'photos_to_drive_downloads': 0,
            'conflicts_resolved': 0,
            'errors': 0
        }
        
        logging.info("Starting synchronization process")
        
        try:
            if log_callback:
                log_callback("Starting synchronization...")
                
            if status_callback:
                status_callback("Scanning Google Drive...")
                
            if progress_callback:
                progress_callback(10)
                
            logging.info(f"Scanning Google Drive folder: {self.drive_folder_id}")
            drive_files = self.drive_manager.get_folder_contents(self.drive_folder_id, recursive=True)
            drive_media_files = [f for f in drive_files if self.drive_manager.is_media_file(f)]
            
            if log_callback:
                log_callback(f"Found {len(drive_media_files)} media files in Google Drive")
                
            logging.info(f"Found {len(drive_media_files)} media files in Google Drive")
                
            if self.stop_requested:
                logging.info("Sync stopped during Drive scanning")
                return
                
            if status_callback:
                status_callback("Scanning Google Photos...")
                
            if progress_callback:
                progress_callback(20)
                
            logging.info("Scanning Google Photos library")
            photos_items = self.photos_manager.get_all_media_items()
            photos_metadata = [self.photos_manager.parse_media_metadata(item) for item in photos_items]
            
            if log_callback:
                log_callback(f"Found {len(photos_metadata)} media items in Google Photos")
                
            logging.info(f"Found {len(photos_metadata)} media items in Google Photos")
                
            if self.stop_requested:
                logging.info("Sync stopped during Photos scanning")
                return
                
            if status_callback:
                status_callback("Comparing files...")
                
            if progress_callback:
                progress_callback(30)
                
            comparison_result = self._compare_files(drive_media_files, photos_metadata, log_callback)
            
            if self.stop_requested:
                logging.info("Sync stopped during file comparison")
                return
                
            if comparison_result['conflicts']:
                if status_callback:
                    status_callback("Resolving conflicts...")
                    
                if log_callback:
                    log_callback(f"Found {len(comparison_result['conflicts'])} potential conflicts to resolve")
                    
                logging.info(f"Resolving {len(comparison_result['conflicts'])} conflicts")
                resolved_conflicts = self._resolve_conflicts(comparison_result['conflicts'], log_callback)
                
                self._update_comparison_with_resolved_conflicts(comparison_result, resolved_conflicts)
                
            if self.stop_requested:
                logging.info("Sync stopped during conflict resolution")
                return
                
            if progress_callback:
                progress_callback(50)
                
            self._perform_sync_operations(comparison_result, progress_callback, status_callback, log_callback)
            
            if log_callback:
                log_callback("Synchronization completed successfully!")
                
            logging.info("Synchronization completed successfully")
            logging.info(f"Stats: {self.stats}")
                
        except Exception as e:
            self.stats['errors'] += 1
            logging.error(f"Synchronization failed: {str(e)}", exc_info=True)
            if log_callback:
                log_callback(f"Synchronization failed: {str(e)}")
            raise
            
    def stop_sync(self) -> None:
        """Stop the synchronization process"""
        self.stop_requested = True
        logging.info("Sync stop requested")
        
    def _compare_files(self, drive_files: list[dict[str, Any]], 
                      photos_metadata: list[dict[str, Any]], 
                      log_callback: Callable[[str], None] | None = None) -> dict[str, list]:
        """Compare files between Drive and Photos
        
        Args:
            drive_files: List of Google Drive file metadata dictionaries
            photos_metadata: List of Google Photos metadata dictionaries
            log_callback: Optional callback for logging progress
            
        Returns:
            Dictionary with categorized results
        """
        logging.info("Starting file comparison between Drive and Photos")
        
        result = {
            'drive_only': [],
            'photos_only': [],
            'matches': [],
            'conflicts': []
        }
        
        drive_by_name_size: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        photos_by_name_size: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        
        logging.debug("Indexing Drive files by name and size")
        for drive_file in drive_files:
            name = drive_file.get('name', '').lower()
            size = int(drive_file.get('size', 0))
            key = (name, size)
            drive_by_name_size[key].append(drive_file)
            
        logging.debug("Indexing Photos files by name")
        for photos_item in photos_metadata:
            name = photos_item.get('filename', '').lower()
            key = (name, 0)
            photos_by_name_size[key].append(photos_item)
            
        logging.debug(f"Indexed {len(drive_by_name_size)} unique Drive files and {len(photos_by_name_size)} unique Photos files")
            
        processed_drive_files = set()
        processed_photos_items = set()
        
        drive_names = {f.get('name', '').lower(): f for f in drive_files}
        photos_names = {p.get('filename', '').lower(): p for p in photos_metadata}
        
        logging.debug("Performing first pass comparison: exact name matches")
        for name in drive_names:
            if name in photos_names:
                drive_file = drive_names[name]
                photos_item = photos_names[name]
                
                if self._are_dates_similar(drive_file, photos_item):
                    result['matches'].append({
                        'drive_file': drive_file,
                        'photos_item': photos_item
                    })
                    logging.debug(f"Match found: {name}")
                else:
                    result['conflicts'].append({
                        'drive_file': drive_file,
                        'photos_item': photos_item
                    })
                    logging.debug(f"Conflict found: {name} (different dates)")
                    
                processed_drive_files.add(drive_file['id'])
                processed_photos_items.add(photos_item['id'])
                
        logging.debug("Performing second pass: finding unmatched files")
        for drive_file in drive_files:
            if drive_file['id'] not in processed_drive_files:
                result['drive_only'].append(drive_file)
                logging.debug(f"Drive-only file found: {drive_file.get('name', 'Unknown')}")
                
        for photos_item in photos_metadata:
            if photos_item['id'] not in processed_photos_items:
                result['photos_only'].append(photos_item)
                logging.debug(f"Photos-only file found: {photos_item.get('filename', 'Unknown')}")
                
        if log_callback:
            log_callback(f"Comparison results:")
            log_callback(f"  - Perfect matches: {len(result['matches'])}")
            log_callback(f"  - Drive only: {len(result['drive_only'])}")
            log_callback(f"  - Photos only: {len(result['photos_only'])}")
            log_callback(f"  - Conflicts: {len(result['conflicts'])}")
            
        logging.info(f"Comparison results: {len(result['matches'])} matches, {len(result['drive_only'])} Drive-only, "
                    f"{len(result['photos_only'])} Photos-only, {len(result['conflicts'])} conflicts")
            
        return result
        
    def _are_dates_similar(self, drive_file: dict[str, Any], photos_item: dict[str, Any], 
                          tolerance_hours: int = 24) -> bool:
        """Check if creation dates are similar within tolerance
        
        Args:
            drive_file: Google Drive file metadata
            photos_item: Google Photos item metadata
            tolerance_hours: Maximum allowed difference in hours
            
        Returns:
            True if dates are within tolerance, False otherwise
        """
        try:
            drive_date_str = drive_file.get('createdTime', '')
            photos_date_str = photos_item.get('creation_time', '')
            
            if not drive_date_str or not photos_date_str:
                logging.debug("Missing date information for comparison")
                return False
                
            drive_date = datetime.fromisoformat(drive_date_str.replace('Z', '+00:00'))
            photos_date = datetime.fromisoformat(photos_date_str.replace('Z', '+00:00'))
            
            diff = abs((drive_date - photos_date).total_seconds()) / 3600
            
            logging.debug(f"Date comparison: Drive={drive_date}, Photos={photos_date}, Diff={diff:.2f} hours")
            return diff <= tolerance_hours
            
        except (ValueError, TypeError) as e:
            logging.error(f"Error comparing dates: {e}")
            return False
            
    def _resolve_conflicts(self, conflicts: list[dict[str, Any]], 
                          log_callback: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
        """Resolve conflicts by asking user
        
        Args:
            conflicts: List of conflict dictionaries
            log_callback: Optional callback for logging progress
            
        Returns:
            List of resolved conflicts with resolution decisions
        """
        resolved = []
        
        for conflict in conflicts:
            if self.stop_requested:
                logging.info("Conflict resolution interrupted by stop request")
                break
                
            drive_file = conflict['drive_file']
            photos_item = conflict['photos_item']
            
            if log_callback:
                log_callback(f"Resolving conflict for: {drive_file.get('name', 'Unknown')}")
                
            logging.info(f"Resolving conflict for: {drive_file.get('name', 'Unknown')}")
                
            resolution = self.conflict_resolver.resolve_conflict(drive_file, photos_item)
            
            resolved.append({
                'drive_file': drive_file,
                'photos_item': photos_item,
                'resolution': resolution
            })
            
            logging.info(f"Conflict for {drive_file.get('name', 'Unknown')} resolved as: {resolution}")
            self.stats['conflicts_resolved'] += 1
            
            if resolution == ConflictResolution.CANCEL:
                if log_callback:
                    log_callback("Sync cancelled by user")
                logging.info("Sync cancelled by user during conflict resolution")
                self.stop_requested = True
                break
                
        return resolved
        
    def _update_comparison_with_resolved_conflicts(self, comparison_result: dict[str, list], 
                                                 resolved_conflicts: list[dict[str, Any]]) -> None:
        """Update comparison results based on conflict resolution
        
        Args:
            comparison_result: The comparison result dictionary to update
            resolved_conflicts: List of resolved conflicts with decisions
        """
        comparison_result['conflicts'] = []
        
        for resolved in resolved_conflicts:
            if resolved['resolution'] == ConflictResolution.SAME:
                comparison_result['matches'].append({
                    'drive_file': resolved['drive_file'],
                    'photos_item': resolved['photos_item']
                })
                logging.debug(f"Conflict resolved as SAME: {resolved['drive_file'].get('name', 'Unknown')}")
            elif resolved['resolution'] == ConflictResolution.DIFFERENT:
                comparison_result['drive_only'].append(resolved['drive_file'])
                comparison_result['photos_only'].append(resolved['photos_item'])
                logging.debug(f"Conflict resolved as DIFFERENT: {resolved['drive_file'].get('name', 'Unknown')}")
                
    def _perform_sync_operations(self, comparison_result: dict[str, list], 
                                progress_callback: Callable[[int], None] | None = None, 
                                status_callback: Callable[[str], None] | None = None, 
                                log_callback: Callable[[str], None] | None = None) -> None:
        """Perform the actual sync operations
        
        Args:
            comparison_result: Dictionary with categorized files
            progress_callback: Optional callback for reporting progress
            status_callback: Optional callback for reporting status
            log_callback: Optional callback for detailed logging
        """
        total_operations = len(comparison_result['drive_only']) + len(comparison_result['photos_only'])
        
        if total_operations == 0:
            logging.info("No sync operations needed - everything is already in sync")
            if log_callback:
                log_callback("No sync operations needed - everything is already in sync!")
            if progress_callback:
                progress_callback(100)
            return
            
        logging.info(f"Performing {total_operations} sync operations")
        completed_operations = 0
        
        for drive_file in comparison_result['drive_only']:
            if self.stop_requested:
                logging.info("Sync operations interrupted by stop request")
                break
                
            if status_callback:
                status_callback(f"Uploading {drive_file['name']} to Google Photos...")
                
            if log_callback:
                log_callback(f"Uploading to Photos: {drive_file['name']}")
                
            success = self._upload_drive_file_to_photos(drive_file, log_callback)
            
            if success:
                self.stats['drive_to_photos_uploads'] += 1
            else:
                self.stats['errors'] += 1
                
            completed_operations += 1
            if progress_callback:
                progress = 50 + (completed_operations / total_operations) * 50
                progress_callback(int(progress))
                
            if not success and log_callback:
                log_callback(f"Failed to upload: {drive_file['name']}")
                
        for photos_item in comparison_result['photos_only']:
            if self.stop_requested:
                logging.info("Sync operations interrupted by stop request")
                break
                
            if status_callback:
                status_callback(f"Downloading {photos_item['filename']} from Google Photos...")
                
            if log_callback:
                log_callback(f"Downloading from Photos: {photos_item['filename']}")
                
            success = self._download_photos_item_to_drive(photos_item, log_callback)
            
            if success:
                self.stats['photos_to_drive_downloads'] += 1
            else:
                self.stats['errors'] += 1
                
            completed_operations += 1
            if progress_callback:
                progress = 50 + (completed_operations / total_operations) * 50
                progress_callback(int(progress))
                
            if not success and log_callback:
                log_callback(f"Failed to download: {photos_item['filename']}")
                
        if progress_callback:
            progress_callback(100)
            
    def _upload_drive_file_to_photos(self, drive_file: dict[str, Any], 
                                    log_callback: Callable[[str], None] | None = None) -> bool:
        """Upload a Drive file to Google Photos
        
        Args:
            drive_file: Google Drive file metadata
            log_callback: Optional callback for logging
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
                
            success = self.drive_manager.download_file(drive_file['id'], temp_path)
            if not success:
                logging.error(f"Failed to download file from Drive: {drive_file['name']}")
                return False
                
            upload_result = self.photos_manager.upload_media_item(temp_path)
            
            try:
                os.unlink(temp_path)
            except OSError:
                pass
                
            if upload_result:
                logging.info(f"Successfully uploaded {drive_file['name']} to Photos")
                return True
            else:
                logging.error(f"Failed to upload {drive_file['name']} to Photos")
                return False
                
        except Exception as e:
            logging.error(f"Error uploading {drive_file['name']} to Photos: {e}")
            return False
            
    def _download_photos_item_to_drive(self, photos_item: dict[str, Any], 
                                      log_callback: Callable[[str], None] | None = None) -> bool:
        """Download a Photos item to Google Drive
        
        Args:
            photos_item: Google Photos item metadata
            log_callback: Optional callback for logging
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
                
            success = self.photos_manager.download_media_item(photos_item['id'], temp_path)
            if not success:
                logging.error(f"Failed to download item from Photos: {photos_item['filename']}")
                return False
                
            upload_result = self.drive_manager.upload_file(
                temp_path, 
                photos_item['filename'], 
                self.drive_folder_id
            )
            
            try:
                os.unlink(temp_path)
            except OSError:
                pass
                
            if upload_result:
                logging.info(f"Successfully downloaded {photos_item['filename']} to Drive")
                return True
            else:
                logging.error(f"Failed to upload {photos_item['filename']} to Drive")
                return False
                
        except Exception as e:
            logging.error(f"Error downloading {photos_item['filename']} to Drive: {e}")
            return False