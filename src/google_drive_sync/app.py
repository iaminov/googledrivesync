#!/usr/bin/env python3
"""
Google Drive & Photos Sync Application

A tool for synchronizing media files between Google Drive and Google Photos.
"""

import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime

from .auth_manager import AuthManager
from .drive_manager import DriveManager
from .photos_manager import PhotosManager
from sync_engine import SyncEngine
from conflict_resolver import ConflictResolver


class Application(tk.Tk):
    """Main application window and controller"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Google Drive & Photos Sync")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Initialize managers
        self.auth_manager = AuthManager()
        self.drive_manager = None
        self.photos_manager = None
        self.sync_engine = None
        self.selected_folder_id = None
        
        # Setup logging
        self.setup_logging()
        
        # Create UI
        self.create_ui()
        
        # Check authentication status on startup
        self.update_auth_status()
    
    def setup_logging(self):
        """Configure application logging"""
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def create_ui(self):
        """Create the application UI"""
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Google Drive & Photos Sync", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Authentication frame
        auth_frame = ttk.LabelFrame(main_frame, text="Authentication", padding="10")
        auth_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.auth_status_label = ttk.Label(auth_frame, text="Not authenticated")
        self.auth_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.auth_button = ttk.Button(auth_frame, text="Authenticate", 
                                     command=self.authenticate)
        self.auth_button.pack(side=tk.LEFT)
        
        self.revoke_button = ttk.Button(auth_frame, text="Revoke Access", 
                                      command=self.revoke_access, state=tk.DISABLED)
        self.revoke_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Google Drive Folder", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.folder_label = ttk.Label(folder_frame, text="No folder selected")
        self.folder_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.select_folder_button = ttk.Button(folder_frame, text="Select Folder", 
                                             command=self.select_folder, state=tk.DISABLED)
        self.select_folder_button.pack(side=tk.LEFT)
        
        # Sync options frame
        options_frame = ttk.LabelFrame(main_frame, text="Sync Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Two-way sync option
        self.two_way_var = tk.BooleanVar(value=True)
        two_way_check = ttk.Checkbutton(options_frame, text="Two-way synchronization", 
                                      variable=self.two_way_var)
        two_way_check.pack(anchor=tk.W)
        
        # Sync buttons frame
        sync_frame = ttk.Frame(main_frame)
        sync_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.start_button = ttk.Button(sync_frame, text="Start Sync", 
                                     command=self.start_sync, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT)
        
        self.stop_button = ttk.Button(sync_frame, text="Stop Sync", 
                                    command=self.stop_sync, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, 
                                          length=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X)
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for log
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=10, yscrollcommand=scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
    
    def update_auth_status(self):
        """Update authentication status display"""
        if self.auth_manager.is_authenticated():
            self.auth_status_label.config(text="Authenticated")
            self.auth_button.config(state=tk.DISABLED)
            self.revoke_button.config(state=tk.NORMAL)
            self.select_folder_button.config(state=tk.NORMAL)
            
            # Initialize services
            self.drive_manager = DriveManager(self.auth_manager.get_drive_service())
            self.photos_manager = PhotosManager(self.auth_manager.get_photos_service())
            
            self.log("Authentication successful")
        else:
            self.auth_status_label.config(text="Not authenticated")
            self.auth_button.config(state=tk.NORMAL)
            self.revoke_button.config(state=tk.DISABLED)
            self.select_folder_button.config(state=tk.DISABLED)
            self.start_button.config(state=tk.DISABLED)
    
    def authenticate(self):
        """Authenticate with Google APIs"""
        try:
            success = self.auth_manager.authenticate()
            self.update_auth_status()
        except Exception as e:
            self.log(f"Authentication error: {str(e)}")
    
    def revoke_access(self):
        """Revoke API access"""
        try:
            self.auth_manager.revoke_credentials()
            self.update_auth_status()
            self.log("Access revoked successfully")
        except Exception as e:
            self.log(f"Error revoking access: {str(e)}")
    
    def select_folder(self):
        """Open folder selection dialog"""
        try:
            folders = self.drive_manager.list_folders()
            
            # Create folder selection dialog
            dialog = tk.Toplevel(self)
            dialog.title("Select Google Drive Folder")
            dialog.geometry("500x400")
            dialog.transient(self)
            dialog.grab_set()
            
            # Center the dialog
            dialog.geometry("+%d+%d" % (
                self.winfo_rootx() + 50, 
                self.winfo_rooty() + 50
            ))
            
            # Frame for folder list
            frame = ttk.Frame(dialog, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Label
            ttk.Label(frame, text="Select a folder to sync:").pack(anchor=tk.W, pady=(0, 10))
            
            # Treeview for folders
            columns = ("name",)
            tree = ttk.Treeview(frame, columns=columns, show="tree headings")
            tree.pack(fill=tk.BOTH, expand=True)
            
            # Add root folder
            root_id = tree.insert("", "end", text="My Drive", values=("My Drive",), 
                                 open=True, tags=("root",))
            
            # Add folders
            for folder in folders:
                tree.insert(root_id, "end", text=folder["name"], values=(folder["name"],), 
                           tags=(folder["id"],))
            
            # Buttons
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, pady=10)
            
            ttk.Button(button_frame, text="Select", 
                      command=lambda: self.on_folder_selected(tree, dialog)).pack(side=tk.LEFT)
            ttk.Button(button_frame, text="Cancel", 
                      command=dialog.destroy).pack(side=tk.LEFT, padx=(10, 0))
            
        except Exception as e:
            self.log(f"Error listing folders: {str(e)}")
    
    def on_folder_selected(self, tree, dialog):
        """Handle folder selection"""
        selected_item = tree.selection()
        if not selected_item:
            return
            
        item_id = selected_item[0]
        folder_name = tree.item(item_id, "text")
        
        # Get the folder ID from tags
        tags = tree.item(item_id, "tags")
        if "root" in tags:
            folder_id = "root"
        else:
            folder_id = tags[0]
        
        self.selected_folder_id = folder_id
        self.folder_label.config(text=folder_name)
        self.start_button.config(state=tk.NORMAL)
        
        self.log(f"Selected folder: {folder_name} (ID: {folder_id})")
        dialog.destroy()
    
    def start_sync(self):
        """Start synchronization process"""
        if not self.selected_folder_id:
            self.log("No folder selected")
            return
            
        try:
            # Create conflict resolver
            conflict_resolver = ConflictResolver(self)
            
            # Create sync engine
            self.sync_engine = SyncEngine(
                self.drive_manager,
                self.photos_manager,
                conflict_resolver,
                self.selected_folder_id
            )
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.progress_bar["value"] = 0
            
            # Start sync in a separate thread
            import threading
            sync_thread = threading.Thread(
                target=self.sync_engine.start_sync,
                kwargs={
                    "progress_callback": self.update_progress,
                    "status_callback": self.update_status,
                    "log_callback": self.log
                }
            )
            sync_thread.daemon = True
            sync_thread.start()
            
        except Exception as e:
            self.log(f"Error starting sync: {str(e)}")
    
    def stop_sync(self):
        """Stop synchronization process"""
        if self.sync_engine:
            self.sync_engine.stop_sync()
            self.log("Sync stopped by user")
            
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar["value"] = value
        self.update_idletasks()
    
    def update_status(self, status):
        """Update status label"""
        self.status_label.config(text=status)
        self.update_idletasks()
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # Also log to system logger
        logging.info(message)


def main():
    """Application entry point"""
    app = Application()
    app.mainloop()


if __name__ == "__main__":
    main()


