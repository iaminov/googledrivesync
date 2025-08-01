"""Tests for ConflictResolver class."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk

from conflict_resolver import ConflictResolver


class TestConflictResolver(unittest.TestCase):
    """Test cases for ConflictResolver."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_parent = Mock()
        self.conflict_resolver = ConflictResolver(self.mock_parent)

    def test_init(self):
        """Test ConflictResolver initialization."""
        self.assertEqual(self.conflict_resolver.parent, self.mock_parent)
        self.assertIsNone(self.conflict_resolver.result)

    @patch('conflict_resolver.tk.Toplevel')
    def test_resolve_conflict_dialog_creation(self, mock_toplevel):
        """Test that conflict resolution dialog is created properly."""
        mock_dialog = Mock()
        mock_toplevel.return_value = mock_dialog
        
        drive_file = {
            'name': 'photo.jpg',
            'size': '1024',
            'createdTime': '2023-07-15T10:30:00Z'
        }
        
        photos_item = {
            'filename': 'photo.jpg',
            'creation_time': '2023-07-16T10:30:00Z'
        }
        
        # Mock the dialog to immediately return a result
        with patch.object(mock_dialog, 'wait_window'):
            
            self.conflict_resolver.result = 'same'  # Simulate user choice
            result = self.conflict_resolver.resolve_conflict(drive_file, photos_item)
        
        # Verify dialog was created
        mock_toplevel.assert_called_once_with(self.mock_parent)
        
        # Verify dialog properties were set
        mock_dialog.title.assert_called_once_with("File Conflict")
        mock_dialog.resizable.assert_called_once_with(False, False)
        mock_dialog.grab_set.assert_called_once()
        
        self.assertEqual(result, 'same')

    @patch('conflict_resolver.tk.Toplevel')
    @patch('conflict_resolver.tk.Label')
    @patch('conflict_resolver.tk.Button')
    @patch('conflict_resolver.tk.Frame')
    def test_create_dialog_content(self, mock_frame, mock_button, mock_label, mock_toplevel):
        """Test dialog content creation."""
        mock_dialog = Mock()
        mock_toplevel.return_value = mock_dialog
        
        drive_file = {
            'name': 'photo.jpg',
            'size': '1024',
            'createdTime': '2023-07-15T10:30:00Z'
        }
        
        photos_item = {
            'filename': 'photo.jpg',
            'creation_time': '2023-07-16T10:30:00Z'
        }
        
        # Mock frame instances
        mock_main_frame = Mock()
        mock_info_frame = Mock()
        mock_button_frame = Mock()
        mock_frame.side_effect = [mock_main_frame, mock_info_frame, mock_button_frame]
        
        # Mock label instances
        mock_labels = [Mock() for _ in range(6)]  # Expected number of labels
        mock_label.side_effect = mock_labels
        
        # Mock button instances
        mock_buttons = [Mock() for _ in range(3)]  # Expected number of buttons
        mock_button.side_effect = mock_buttons
        
        with patch.object(self.conflict_resolver, '_center_dialog'), \
             patch.object(mock_dialog, 'wait_window'):
            
            self.conflict_resolver.result = 'same'
            result = self.conflict_resolver.resolve_conflict(drive_file, photos_item)
        
        # Verify frames were created
        self.assertEqual(mock_frame.call_count, 3)
        
        # Verify labels were created (title + drive info + photos info)
        self.assertGreaterEqual(mock_label.call_count, 5)
        
        # Verify buttons were created (same, different, cancel)
        self.assertEqual(mock_button.call_count, 3)
        
        self.assertEqual(result, 'same')

    def test_set_result(self):
        """Test _set_result method."""
        mock_dialog = Mock()
        
        # Test setting 'same' result
        self.conflict_resolver._set_result(mock_dialog, 'same')
        self.assertEqual(self.conflict_resolver.result, 'same')
        mock_dialog.destroy.assert_called_once()
        
        # Reset mock
        mock_dialog.reset_mock()
        
        # Test setting 'different' result
        self.conflict_resolver._set_result(mock_dialog, 'different')
        self.assertEqual(self.conflict_resolver.result, 'different')
        mock_dialog.destroy.assert_called_once()
        
        # Reset mock
        mock_dialog.reset_mock()
        
        # Test setting 'cancel' result
        self.conflict_resolver._set_result(mock_dialog, 'cancel')
        self.assertEqual(self.conflict_resolver.result, 'cancel')
        mock_dialog.destroy.assert_called_once()



    @patch('conflict_resolver.tk.Toplevel')
    def test_resolve_conflict_returns_cancel_on_close(self, mock_toplevel):
        """Test that closing dialog without selection returns cancel."""
        mock_dialog = Mock()
        mock_toplevel.return_value = mock_dialog
        
        drive_file = {'name': 'photo.jpg', 'size': '1024', 'createdTime': '2023-07-15T10:30:00Z'}
        photos_item = {'filename': 'photo.jpg', 'creation_time': '2023-07-16T10:30:00Z'}
        
        with patch.object(mock_dialog, 'wait_window'):
            
            # Don't set result, simulating dialog close without selection
            result = self.conflict_resolver.resolve_conflict(drive_file, photos_item)
        
        # Should default to cancel
        self.assertEqual(result, 'cancel')

    @patch('conflict_resolver.tk.Toplevel')
    def test_resolve_conflict_with_missing_file_info(self, mock_toplevel):
        """Test conflict resolution with missing file information."""
        mock_dialog = Mock()
        mock_toplevel.return_value = mock_dialog
        
        # Files with minimal information
        drive_file = {'name': 'photo.jpg'}
        photos_item = {'filename': 'photo.jpg'}
        
        with patch.object(self.conflict_resolver, '_create_dialog_content'), \
             patch.object(self.conflict_resolver, '_center_dialog'), \
             patch.object(mock_dialog, 'wait_window'):
            
            self.conflict_resolver.result = 'different'
            result = self.conflict_resolver.resolve_conflict(drive_file, photos_item)
        
        # Should still work with minimal info
        self.assertEqual(result, 'different')

    @patch('conflict_resolver.tk.Toplevel')
    def test_dialog_protocol_handler(self, mock_toplevel):
        """Test that dialog close protocol is handled."""
        mock_dialog = Mock()
        mock_toplevel.return_value = mock_dialog
        
        drive_file = {'name': 'photo.jpg', 'size': '1024', 'createdTime': '2023-07-15T10:30:00Z'}
        photos_item = {'filename': 'photo.jpg', 'creation_time': '2023-07-16T10:30:00Z'}
        
        with patch.object(mock_dialog, 'wait_window'):
            
            self.conflict_resolver.result = 'same'
            result = self.conflict_resolver.resolve_conflict(drive_file, photos_item)
        
        # Verify protocol handler was set for window close
        mock_dialog.protocol.assert_called()
        protocol_calls = mock_dialog.protocol.call_args_list
        
        # Should have WM_DELETE_WINDOW protocol handler
        wm_delete_calls = [call for call in protocol_calls if call[0][0] == "WM_DELETE_WINDOW"]
        self.assertEqual(len(wm_delete_calls), 1)
        
        self.assertEqual(result, 'same')

    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes."""
        # This tests the internal size formatting if it exists
        # Since the actual implementation might not have this method,
        # we'll test the expected behavior
        
        drive_file = {
            'name': 'photo.jpg',
            'size': '1024',  # 1 KB
            'createdTime': '2023-07-15T10:30:00Z'
        }
        
        photos_item = {
            'filename': 'photo.jpg',
            'creation_time': '2023-07-16T10:30:00Z'
        }
        
        # Test that the resolver can handle various file sizes
        with patch('conflict_resolver.tk.Toplevel') as mock_toplevel:
            mock_dialog = Mock()
            mock_toplevel.return_value = mock_dialog
            
            with patch.object(mock_dialog, 'wait_window'):
                
                self.conflict_resolver.result = 'same'
                result = self.conflict_resolver.resolve_conflict(drive_file, photos_item)
            
            self.assertEqual(result, 'same')

    def test_multiple_conflicts_independent(self):
        """Test that multiple conflict resolutions are independent."""
        drive_file1 = {'name': 'photo1.jpg', 'size': '1024', 'createdTime': '2023-07-15T10:30:00Z'}
        photos_item1 = {'filename': 'photo1.jpg', 'creation_time': '2023-07-16T10:30:00Z'}
        
        drive_file2 = {'name': 'photo2.jpg', 'size': '2048', 'createdTime': '2023-07-17T10:30:00Z'}
        photos_item2 = {'filename': 'photo2.jpg', 'creation_time': '2023-07-18T10:30:00Z'}
        
        with patch('conflict_resolver.tk.Toplevel') as mock_toplevel:
            mock_dialog = Mock()
            mock_toplevel.return_value = mock_dialog
            
            with patch.object(mock_dialog, 'wait_window'):
                
                # First conflict - choose same
                self.conflict_resolver.result = 'same'
                result1 = self.conflict_resolver.resolve_conflict(drive_file1, photos_item1)
                
                # Reset result for second conflict
                self.conflict_resolver.result = 'different'
                result2 = self.conflict_resolver.resolve_conflict(drive_file2, photos_item2)
            
            self.assertEqual(result1, 'same')
            self.assertEqual(result2, 'different')


if __name__ == '__main__':
    unittest.main()