"""
Conflict Resolver
Handles conflicts when same filename/size but different dates are found
"""

import io
import logging
import os
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

import requests
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class ConflictResolution(Enum):
    """Enum representing possible conflict resolution choices"""
    SAME_FILE = auto()
    DIFFERENT_FILES = auto()
    CANCEL = auto()


class ConflictResolver:
    """Handles conflicts between files with same name/size but different dates"""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.result: Optional[str] = None
        self.drive_image: Optional[ImageTk.PhotoImage] = None
        self.photos_image: Optional[ImageTk.PhotoImage] = None
        
    def resolve_conflict(self, drive_file: Dict[str, Any], photos_item: Dict[str, Any]) -> str:
        """
        Show dialog to resolve conflict between files with same name/size but different dates
        
        Args:
            drive_file: Google Drive file metadata
            photos_item: Google Photos item metadata
            
        Returns: 
            'same', 'different', or 'cancel'
        """
        self.result = None
        logging.debug(f"Resolving conflict for {drive_file.get('name', 'unknown')}")
        
        # Create conflict resolution dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Resolve File Conflict")
        dialog.geometry("700x500")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50, 
            self.parent.winfo_rooty() + 50
        ))
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="File Conflict Detected", 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_text = ("The following files have the same name and size but different creation dates. "
                    "Please review the information below and decide if they are the same file or different files.")
        desc_label = ttk.Label(main_frame, text=desc_text, wraplength=650, justify=tk.LEFT)
        desc_label.pack(pady=(0, 20))
        
        # Create comparison frame
        comparison_frame = ttk.Frame(main_frame)
        comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Google Drive file info
        drive_frame = ttk.LabelFrame(comparison_frame, text="Google Drive File", padding="10")
        drive_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self._add_file_info(drive_frame, drive_file, is_drive=True)
        
        # Google Photos file info
        photos_frame = ttk.LabelFrame(comparison_frame, text="Google Photos File", padding="10")
        photos_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self._add_file_info(photos_frame, photos_item, is_drive=False)
        
        # Decision buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Explanation
        explanation = ttk.Label(button_frame, 
                               text="Are these the same file?", 
                               font=('TkDefaultFont', 10, 'bold'))
        explanation.pack(pady=(0, 10))
        
        # Buttons
        btn_frame = ttk.Frame(button_frame)
        btn_frame.pack()
        
        ttk.Button(btn_frame, text="Yes, same file", 
                  command=lambda: self._set_result(dialog, 'same')).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="No, different files", 
                  command=lambda: self._set_result(dialog, 'different')).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Cancel", 
                  command=lambda: self._set_result(dialog, 'cancel')).pack(side=tk.LEFT)
        
        # Wait for user decision
        dialog.wait_window()
        return self.result
        
    def _add_file_info(self, parent_frame: ttk.Frame, file_info: Dict[str, Any], is_drive: bool = True) -> None:
        """Add file information to the frame
        
        Args:
            parent_frame: The parent frame to add information to
            file_info: Dictionary containing file metadata
            is_drive: Whether this is Drive (True) or Photos (False) file
        """
        info_frame = ttk.Frame(parent_frame)
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        if is_drive:
            # Google Drive file info
            self._add_info_row(info_frame, "Name:", file_info.get('name', 'Unknown'))
            self._add_info_row(info_frame, "Size:", self._format_size(file_info.get('size', '0')))
            self._add_info_row(info_frame, "Created:", self._format_datetime(file_info.get('createdTime', '')))
            self._add_info_row(info_frame, "Modified:", self._format_datetime(file_info.get('modifiedTime', '')))
            self._add_info_row(info_frame, "MIME Type:", file_info.get('mimeType', 'Unknown'))
        else:
            # Google Photos file info
            metadata = file_info
            self._add_info_row(info_frame, "Name:", metadata.get('filename', 'Unknown'))
            self._add_info_row(info_frame, "Size:", "Unknown")  # Photos API doesn't provide size
            self._add_info_row(info_frame, "Created:", self._format_datetime(metadata.get('creation_time', '')))
            self._add_info_row(info_frame, "MIME Type:", metadata.get('mime_type', 'Unknown'))
            self._add_info_row(info_frame, "Dimensions:", f"{metadata.get('width', 'Unknown')} x {metadata.get('height', 'Unknown')}")
            
            if metadata.get('is_photo'):
                self._add_info_row(info_frame, "Type:", "Photo")
                if metadata.get('camera_make'):
                    self._add_info_row(info_frame, "Camera:", f"{metadata.get('camera_make')} {metadata.get('camera_model', '')}")
            elif metadata.get('is_video'):
                self._add_info_row(info_frame, "Type:", "Video")
                if metadata.get('fps'):
                    self._add_info_row(info_frame, "FPS:", str(metadata.get('fps')))
                    
    def _add_info_row(self, parent: ttk.Frame, label: str, value: str) -> None:
        """Add a label-value row to the info frame
        
        Args:
            parent: Parent frame to add the row to
            label: Label text
            value: Value text
        """
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)
        
        label_widget = ttk.Label(row_frame, text=label, font=('TkDefaultFont', 9, 'bold'))
        label_widget.pack(side=tk.LEFT, anchor=tk.W)
        
        value_widget = ttk.Label(row_frame, text=str(value), wraplength=250)
        value_widget.pack(side=tk.LEFT, anchor=tk.W, padx=(10, 0))
        
    def _format_size(self, size_str: Union[str, int]) -> str:
        """Format file size in human readable format
        
        Args:
            size_str: Size in bytes as string or int
            
        Returns:
            Human-readable size string
        """
        try:
            size = int(size_str)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except (ValueError, TypeError):
            logging.warning(f"Could not format size: {size_str}")
            return "Unknown"
            
    def _format_datetime(self, datetime_str: Optional[str]) -> str:
        """Format datetime string in readable format
        
        Args:
            datetime_str: ISO format datetime string
            
        Returns:
            Formatted datetime string
        """
        if not datetime_str:
            return "Unknown"
            
        try:
            # Parse ISO format datetime
            if 'T' in datetime_str:
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return datetime_str
        except (ValueError, TypeError) as e:
            logging.warning(f"Failed to parse datetime {datetime_str}: {e}")
            return datetime_str
            
    def _set_result(self, dialog: tk.Toplevel, result: str) -> None:
        """Set the result and close dialog
        
        Args:
            dialog: The dialog window to close
            result: The resolution result ('same', 'different', or 'cancel')
        """
        logging.debug(f"User selected: {result}")
        self.result = result
        dialog.destroy()