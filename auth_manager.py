"""
Authentication Manager for Google APIs
Handles OAuth2 authentication for Google Drive and Google Photos
"""

import os
import pickle
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class AuthManager:
    """Manages authentication with Google APIs for Drive and Photos services"""
    
    # Scopes required for the application
    SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/photoslibrary',
        'https://www.googleapis.com/auth/photoslibrary.sharing'
    ]
    
    def __init__(self, token_dir: str | None = None):
        """Initialize the authentication manager
        
        Args:
            token_dir: Optional directory to store token files. Defaults to current directory.
        """
        self.credentials = None
        self.drive_service = None
        self.photos_service = None
        
        # Set token directory
        self.token_dir = Path(token_dir) if token_dir else Path.cwd()
        self.token_dir.mkdir(exist_ok=True)
        
        self.token_file = self.token_dir / 'token.pickle'
        
        # Get credentials file path from environment variable or use default
        self.credentials_file = os.environ.get('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        
    def authenticate(self) -> bool:
        """Authenticate with Google APIs
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            # Load existing credentials
            if self.token_file.exists():
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
                    logging.debug("Loaded existing credentials from token file")
                    
            # If there are no valid credentials, get new ones
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    # Refresh expired credentials
                    logging.info("Refreshing expired credentials")
                    self.credentials.refresh(Request())
                else:
                    # Get new credentials
                    credentials_path = Path(self.credentials_file)
                    if not credentials_path.exists():
                        raise FileNotFoundError(
                            f"Credentials file '{self.credentials_file}' not found. "
                            "Please download it from Google Cloud Console and place it in the project directory "
                            "or set the GOOGLE_CREDENTIALS_FILE environment variable."
                        )
                    
                    logging.info("Obtaining new credentials via OAuth flow")    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path), self.SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                    
                # Save credentials for next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.credentials, token)
                    logging.debug("Saved credentials to token file")
                    
            # Build service objects
            logging.info("Building service objects")
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.photos_service = build('photoslibrary', 'v1', credentials=self.credentials)
            
            return True
            
        except Exception as e:
            logging.error(f"Authentication failed: {str(e)}")
            return False
            
    def get_drive_service(self):
        """Get Google Drive service object"""
        if not self.drive_service:
            raise ValueError("Not authenticated. Call authenticate() first.")
        return self.drive_service
        
    def get_photos_service(self):
        """Get Google Photos service object"""
        if not self.photos_service:
            raise ValueError("Not authenticated. Call authenticate() first.")
        return self.photos_service
        
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.credentials is not None and self.credentials.valid
        
    def revoke_credentials(self) -> None:
        """Revoke stored credentials"""
        if self.token_file.exists():
            self.token_file.unlink()
            logging.info("Credentials revoked and token file deleted")
            
        self.credentials = None
        self.drive_service = None
        self.photos_service = None