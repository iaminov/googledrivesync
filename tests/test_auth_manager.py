"""Tests for AuthManager class."""

import os
import pickle
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource

from auth_manager import AuthManager


class TestAuthManager(unittest.TestCase):
    """Test cases for AuthManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.token_dir = Path(self.temp_dir)
        self.credentials_file = self.token_dir / "test_credentials.json"
        
        # Create mock credentials file
        self.credentials_file.write_text('{"test": "credentials"}')
        
        # Set environment variable for credentials
        os.environ['GOOGLE_CREDENTIALS_FILE'] = str(self.credentials_file)
        
        self.auth_manager = AuthManager(token_dir=str(self.token_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        if 'GOOGLE_CREDENTIALS_FILE' in os.environ:
            del os.environ['GOOGLE_CREDENTIALS_FILE']
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_token_directory(self):
        """Test that initialization creates token directory."""
        new_dir = self.token_dir / "new_token_dir"
        auth_manager = AuthManager(token_dir=str(new_dir))
        self.assertTrue(new_dir.exists())

    def test_init_uses_current_directory_when_no_token_dir(self):
        """Test that initialization uses current directory when no token_dir provided."""
        auth_manager = AuthManager()
        self.assertEqual(auth_manager.token_dir, Path.cwd())

    @patch('auth_manager.build')
    @patch('auth_manager.InstalledAppFlow')
    def test_authenticate_new_credentials(self, mock_flow_class, mock_build):
        """Test authentication with new credentials."""
        # Mock flow and credentials
        mock_flow = Mock()
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.expired = False
        mock_flow.run_local_server.return_value = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        
        # Mock service builds
        mock_drive_service = Mock(spec=Resource)
        mock_photos_service = Mock(spec=Resource)
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        result = self.auth_manager.authenticate()
        
        self.assertTrue(result)
        self.assertEqual(self.auth_manager.credentials, mock_credentials)
        self.assertEqual(self.auth_manager.drive_service, mock_drive_service)
        self.assertEqual(self.auth_manager.photos_service, mock_photos_service)
        
        # Verify token was saved
        self.assertTrue(self.auth_manager.token_file.exists())

    @patch('auth_manager.build')
    def test_authenticate_existing_valid_credentials(self, mock_build):
        """Test authentication with existing valid credentials."""
        # Create mock credentials and save to token file
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.valid = True
        mock_credentials.expired = False
        
        with open(self.auth_manager.token_file, 'wb') as f:
            pickle.dump(mock_credentials, f)
        
        # Mock service builds
        mock_drive_service = Mock(spec=Resource)
        mock_photos_service = Mock(spec=Resource)
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        result = self.auth_manager.authenticate()
        
        self.assertTrue(result)
        self.assertEqual(self.auth_manager.credentials, mock_credentials)

    @patch('auth_manager.build')
    def test_authenticate_refresh_expired_credentials(self, mock_build):
        """Test authentication with expired but refreshable credentials."""
        # Create mock expired credentials with refresh token
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"
        
        with open(self.auth_manager.token_file, 'wb') as f:
            pickle.dump(mock_credentials, f)
        
        # Mock refresh to make credentials valid
        def mock_refresh(request):
            mock_credentials.valid = True
            mock_credentials.expired = False
        
        mock_credentials.refresh = mock_refresh
        
        # Mock service builds
        mock_drive_service = Mock(spec=Resource)
        mock_photos_service = Mock(spec=Resource)
        mock_build.side_effect = [mock_drive_service, mock_photos_service]
        
        result = self.auth_manager.authenticate()
        
        self.assertTrue(result)
        self.assertTrue(mock_credentials.valid)

    def test_authenticate_missing_credentials_file(self):
        """Test authentication fails when credentials file is missing."""
        self.credentials_file.unlink()
        
        result = self.auth_manager.authenticate()
        
        self.assertFalse(result)

    def test_get_drive_service_not_authenticated(self):
        """Test get_drive_service raises error when not authenticated."""
        with self.assertRaises(ValueError) as context:
            self.auth_manager.get_drive_service()
        
        self.assertIn("Not authenticated", str(context.exception))

    def test_get_photos_service_not_authenticated(self):
        """Test get_photos_service raises error when not authenticated."""
        with self.assertRaises(ValueError) as context:
            self.auth_manager.get_photos_service()
        
        self.assertIn("Not authenticated", str(context.exception))

    def test_is_authenticated_false_when_no_credentials(self):
        """Test is_authenticated returns False when no credentials."""
        self.assertFalse(self.auth_manager.is_authenticated())

    def test_is_authenticated_false_when_invalid_credentials(self):
        """Test is_authenticated returns False when credentials are invalid."""
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.valid = False
        self.auth_manager.credentials = mock_credentials
        
        self.assertFalse(self.auth_manager.is_authenticated())

    def test_is_authenticated_true_when_valid_credentials(self):
        """Test is_authenticated returns True when credentials are valid."""
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.valid = True
        self.auth_manager.credentials = mock_credentials
        
        self.assertTrue(self.auth_manager.is_authenticated())

    def test_revoke_credentials(self):
        """Test revoking credentials clears state and deletes token file."""
        # Set up authenticated state
        mock_credentials = Mock(spec=Credentials)
        self.auth_manager.credentials = mock_credentials
        self.auth_manager.drive_service = Mock()
        self.auth_manager.photos_service = Mock()
        
        # Create token file
        with open(self.auth_manager.token_file, 'wb') as f:
            pickle.dump(mock_credentials, f)
        
        self.auth_manager.revoke_credentials()
        
        self.assertIsNone(self.auth_manager.credentials)
        self.assertIsNone(self.auth_manager.drive_service)
        self.assertIsNone(self.auth_manager.photos_service)
        self.assertFalse(self.auth_manager.token_file.exists())

    def test_revoke_credentials_no_token_file(self):
        """Test revoking credentials when no token file exists."""
        # Ensure no token file exists
        if self.auth_manager.token_file.exists():
            self.auth_manager.token_file.unlink()
        
        # Should not raise an exception
        self.auth_manager.revoke_credentials()
        
        self.assertIsNone(self.auth_manager.credentials)


if __name__ == '__main__':
    unittest.main()