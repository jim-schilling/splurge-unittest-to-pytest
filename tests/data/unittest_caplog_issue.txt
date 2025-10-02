"""Tests for the file_manager module."""

import json
import logging
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from splurge_key_custodian.file_manager import FileManager
from splurge_key_custodian.models import (
    KeyCustodianData, 
    MasterKey, 
    Credential, 
    CredentialData, 
    CredentialFile, 
    CredentialsIndex,
    RotationBackup
)
from splurge_key_custodian.exceptions import FileOperationError


class TestFileManager(unittest.TestCase):
    """Test cases for the FileManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FileManager(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test FileManager initialization."""
        self.assertEqual(self.file_manager.data_directory, Path(self.temp_dir))
        self.assertEqual(self.file_manager.master_file_path, Path(self.temp_dir) / "key-custodian-master.json")
        self.assertEqual(self.file_manager.index_file_path, Path(self.temp_dir) / "key-custodian-index.json")
        
        # Check that directory was created
        self.assertTrue(Path(self.temp_dir).exists())

    def test_initialization_creates_directory(self):
        """Test that initialization creates the data directory."""
        new_dir = os.path.join(self.temp_dir, "new_dir")
        file_manager = FileManager(new_dir)
        
        self.assertTrue(Path(new_dir).exists())

    def test_initialization_creates_nested_directory(self):
        """Test that initialization creates nested directories."""
        nested_dir = os.path.join(self.temp_dir, "nested", "deep", "directory")
        file_manager = FileManager(nested_dir)
        
        self.assertTrue(Path(nested_dir).exists())

    def test_write_json_atomic_success(self):
        """Test successful atomic JSON write."""
        test_data = {"test": "data", "number": 42}
        test_file = Path(self.temp_dir) / "test.json"
        
        self.file_manager._write_json_atomic(test_file, test_data)
        
        # Check that file exists and contains correct data
        self.assertTrue(test_file.exists())
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data, test_data)

    def test_write_json_atomic_overwrites_existing(self):
        """Test atomic JSON write overwrites existing file."""
        test_file = Path(self.temp_dir) / "test.json"
        old_data = {"old": "data"}
        new_data = {"new": "data"}
        
        # Write initial data
        with open(test_file, 'w') as f:
            json.dump(old_data, f)
        
        # Overwrite with new data
        self.file_manager._write_json_atomic(test_file, new_data)
        
        # Check that new data is there
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data, new_data)

    @patch('splurge_key_custodian.file_manager.shutil.move')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_json_atomic_cleanup_on_error(self, mock_file, mock_move):
        """Test cleanup of temporary files on error."""
        test_file = Path(self.temp_dir) / "test.json"
        test_data = {"test": "data"}
        
        # Make shutil.move raise an exception
        mock_move.side_effect = OSError("Move failed")
        
        with self.assertRaises(FileOperationError):
            self.file_manager._write_json_atomic(test_file, test_data)
        
        # Check that temp file was cleaned up
        temp_file = test_file.with_suffix(".temp")
        self.assertFalse(temp_file.exists())

    def test_read_json_existing_file(self):
        """Test reading JSON from existing file."""
        test_data = {"test": "data", "number": 42}
        test_file = Path(self.temp_dir) / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        result = self.file_manager._read_json(test_file)
        self.assertEqual(result, test_data)

    def test_read_json_nonexistent_file(self):
        """Test reading JSON from non-existent file."""
        test_file = Path(self.temp_dir) / "nonexistent.json"
        
        result = self.file_manager._read_json(test_file)
        self.assertIsNone(result)

    def test_read_json_invalid_json(self):
        """Test reading invalid JSON file."""
        test_file = Path(self.temp_dir) / "invalid.json"
        
        with open(test_file, 'w') as f:
            f.write('{"invalid": json}')
        
        with self.assertRaises(FileOperationError):
            self.file_manager._read_json(test_file)

    def test_save_master_keys(self):
        """Test saving master keys."""
        master_keys = [
            {"key_id": "key1", "salt": "salt1", "iterations": 100000, "created_at": "2023-01-01T00:00:00Z"},
            {"key_id": "key2", "salt": "salt2", "iterations": 200000, "created_at": "2023-01-02T00:00:00Z"}
        ]
        
        self.file_manager.save_master_keys(master_keys)
        
        # Check that file was created
        self.assertTrue(self.file_manager._master_file.exists())
        
        # Check file content
        with open(self.file_manager._master_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["master_keys"], master_keys)
        self.assertEqual(data["version"], "1.0")

    def test_read_master_keys_existing(self):
        """Test reading existing master keys."""
        master_keys = [
            {"key_id": "key1", "salt": "salt1", "iterations": 100000, "created_at": "2023-01-01T00:00:00Z"}
        ]
        
        # Save master keys first
        self.file_manager.save_master_keys(master_keys)
        
        # Read them back
        result = self.file_manager.read_master_keys()
        
        self.assertIsNotNone(result)
        self.assertEqual(result["master_keys"], master_keys)
        self.assertEqual(result["version"], "1.0")

    def test_read_master_keys_nonexistent(self):
        """Test reading non-existent master keys."""
        result = self.file_manager.read_master_keys()
        self.assertIsNone(result)

    def test_save_credentials_index(self):
        """Test saving credentials index."""
        index = CredentialsIndex()
        index.add_credential("key1", "Credential 1")
        index.add_credential("key2", "Credential 2")
        
        self.file_manager.save_credentials_index(index)
        
        # Check that file was created
        self.assertTrue(self.file_manager._index_file.exists())
        
        # Check file content
        with open(self.file_manager._index_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["credentials"]["key1"], "Credential 1")
        self.assertEqual(data["credentials"]["key2"], "Credential 2")

    def test_read_credentials_index_existing(self):
        """Test reading existing credentials index."""
        index = CredentialsIndex()
        index.add_credential("key1", "Credential 1")
        
        # Save index first
        self.file_manager.save_credentials_index(index)
        
        # Read it back
        result = self.file_manager.read_credentials_index()
        
        self.assertIsNotNone(result)
        self.assertEqual(result.credentials["key1"], "Credential 1")

    def test_read_credentials_index_nonexistent(self):
        """Test reading non-existent credentials index."""
        result = self.file_manager.read_credentials_index()
        self.assertIsNone(result)

    def test_read_credentials_index_invalid_data(self):
        """Test reading invalid credentials index data."""
        # Write invalid JSON to index file
        with open(self.file_manager._index_file, 'w') as f:
            f.write('{"invalid": json}')
        
        with self.assertRaises(FileOperationError):
            self.file_manager.read_credentials_index()

    def test_save_credential_file(self):
        """Test saving credential file."""
        credential_file = CredentialFile(
            name="Test Credential",
            key_id="test-key",
            salt="test-salt",
            data="encrypted-data",
            created_at="2023-01-01T00:00:00Z"
        )
        
        self.file_manager.save_credential_file("test-key", credential_file)
        
        # Check that file was created
        credential_path = self.file_manager.data_directory / "test-key.credential.json"
        self.assertTrue(credential_path.exists())
        
        # Check file content
        with open(credential_path, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["key_id"], "test-key")
        self.assertEqual(data["salt"], "test-salt")
        self.assertEqual(data["data"], "encrypted-data")

    def test_read_credential_file(self):
        """Test reading credential file."""
        credential_file = CredentialFile(
            name="Test Credential",
            key_id="test-key",
            salt="test-salt",
            data="encrypted-data",
            created_at="2023-01-01T00:00:00Z"
        )
        
        # Save credential file first
        self.file_manager.save_credential_file("test-key", credential_file)
        
        # Read it back
        result = self.file_manager.read_credential_file("test-key")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.key_id, "test-key")
        self.assertEqual(result.salt, "test-salt")
        self.assertEqual(result.data, "encrypted-data")

    def test_read_credential_file_nonexistent(self):
        """Test reading non-existent credential file."""
        result = self.file_manager.read_credential_file("nonexistent-key")
        self.assertIsNone(result)

    def test_read_credential_file_invalid_data(self):
        """Test reading invalid credential file data."""
        credential_path = self.file_manager.data_directory / "test-key.credential.json"
        
        # Write invalid JSON
        with open(credential_path, 'w') as f:
            f.write('{"invalid": json}')
        
        with self.assertRaises(FileOperationError):
            self.file_manager.read_credential_file("test-key")

    def test_delete_credential_file(self):
        """Test deleting credential file."""
        credential_file = CredentialFile(
            name="Test Credential",
            key_id="test-key",
            salt="test-salt",
            data="encrypted-data",
            created_at="2023-01-01T00:00:00Z"
        )
        
        # Save credential file first
        self.file_manager.save_credential_file("test-key", credential_file)
        
        # Verify file exists
        credential_path = self.file_manager.data_directory / "test-key.credential.json"
        self.assertTrue(credential_path.exists())
        
        # Delete it
        self.file_manager.delete_credential_file("test-key")
        
        # Verify file is gone
        self.assertFalse(credential_path.exists())

    def test_delete_credential_file_nonexistent(self):
        """Test deleting non-existent credential file."""
        # Should not raise an exception
        self.file_manager.delete_credential_file("nonexistent-key")

    def test_list_credential_files(self):
        """Test listing credential files."""
        # Create some credential files
        credential_file1 = CredentialFile(
            name="Credential 1",
            key_id="key1",
            salt="salt1",
            data="data1",
            created_at="2023-01-01T00:00:00Z"
        )
        credential_file2 = CredentialFile(
            name="Credential 2",
            key_id="key2",
            salt="salt2",
            data="data2",
            created_at="2023-01-02T00:00:00Z"
        )
        
        self.file_manager.save_credential_file("key1", credential_file1)
        self.file_manager.save_credential_file("key2", credential_file2)
        
        # List files
        files = self.file_manager.list_credential_files()
        
        self.assertEqual(len(files), 2)
        self.assertIn("key1", files)
        self.assertIn("key2", files)

    def test_list_credential_files_empty(self):
        """Test listing credential files when none exist."""
        files = self.file_manager.list_credential_files()
        self.assertEqual(files, [])

    def test_backup_files(self):
        """Test backing up files."""
        # Create some files to backup
        master_keys = [{"key_id": "key1", "salt": "salt1", "iterations": 100000, "created_at": "2023-01-01T00:00:00Z"}]
        self.file_manager.save_master_keys(master_keys)
        
        index = CredentialsIndex()
        index.add_credential("key1", "Credential 1")
        self.file_manager.save_credentials_index(index)
        
        credential_file = CredentialFile(
            name="Credential 1",
            key_id="key1",
            salt="salt1",
            data="data1",
            created_at="2023-01-01T00:00:00Z"
        )
        self.file_manager.save_credential_file("key1", credential_file)
        
        # Create backup
        backup_dir = os.path.join(self.temp_dir, "backup")
        self.file_manager.backup_files(backup_dir)
        
        # Check backup files exist
        backup_path = Path(backup_dir)
        self.assertTrue((backup_path / "key-custodian-master.json").exists())
        self.assertTrue((backup_path / "key-custodian-index.json").exists())
        self.assertTrue((backup_path / "key1.credential.json").exists())

    def test_backup_files_nonexistent_source(self):
        """Test backing up when source files don't exist."""
        backup_dir = os.path.join(self.temp_dir, "backup")
        
        # Should not raise an exception
        self.file_manager.backup_files(backup_dir)
        
        # Backup directory should be created
        self.assertTrue(Path(backup_dir).exists())

    def test_backup_files_creates_directory(self):
        """Test that backup creates the backup directory."""
        backup_dir = os.path.join(self.temp_dir, "nested", "backup", "dir")
        
        self.file_manager.backup_files(backup_dir)
        
        self.assertTrue(Path(backup_dir).exists())

    def test_cleanup_temp_files(self):
        """Test cleaning up temporary files."""
        # Create some temp files
        temp_file1 = self.file_manager.data_directory / "test1.temp"
        temp_file2 = self.file_manager.data_directory / "test2.temp"
        
        with open(temp_file1, 'w') as f:
            f.write("temp1")
        with open(temp_file2, 'w') as f:
            f.write("temp2")
        
        # Verify temp files exist
        self.assertTrue(temp_file1.exists())
        self.assertTrue(temp_file2.exists())
        
        # Clean up
        self.file_manager.cleanup_temp_files()
        
        # Verify temp files are gone
        self.assertFalse(temp_file1.exists())
        self.assertFalse(temp_file2.exists())

    def test_cleanup_temp_files_no_files(self):
        """Test cleaning up when no temp files exist."""
        # Should not raise an exception
        self.file_manager.cleanup_temp_files()

    def test_cleanup_temp_files_error(self):
        """Test cleaning up temp files with error."""
        # Create a temp file
        temp_file = self.file_manager.data_directory / "test.temp"
        with open(temp_file, 'w') as f:
            f.write("temp")
        
        # Mock os.remove to raise an exception
        with patch('os.remove', side_effect=OSError("Permission denied")):
            # Should not raise an exception
            self.file_manager.cleanup_temp_files()

    def test_properties(self):
        """Test FileManager properties."""
        self.assertEqual(self.file_manager.data_directory, Path(self.temp_dir))
        self.assertEqual(self.file_manager.master_file_path, Path(self.temp_dir) / "key-custodian-master.json")
        self.assertEqual(self.file_manager.index_file_path, Path(self.temp_dir) / "key-custodian-index.json")

    def test_write_json_atomic_creates_archive(self):
        """Test that atomic write creates archive of existing file."""
        test_file = Path(self.temp_dir) / "test.json"
        old_data = {"old": "data"}
        new_data = {"new": "data"}
        
        # Write initial data
        with open(test_file, 'w') as f:
            json.dump(old_data, f)
        
        # Overwrite with new data
        self.file_manager._write_json_atomic(test_file, new_data)
        
        # Check that archive file was created and then removed
        archive_file = test_file.with_suffix(".archive")
        self.assertFalse(archive_file.exists())  # Should be cleaned up

    def test_write_json_atomic_no_existing_file(self):
        """Test atomic write when no existing file."""
        test_file = Path(self.temp_dir) / "test.json"
        test_data = {"test": "data"}
        
        self.file_manager._write_json_atomic(test_file, test_data)
        
        # Check that file was created
        self.assertTrue(test_file.exists())
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data, test_data)

    def test_write_json_atomic_json_error(self):
        """Test atomic write with JSON encoding error."""
        test_file = Path(self.temp_dir) / "test.json"
        
        # Create data that can't be JSON serialized
        test_data = {"test": object()}  # object() is not JSON serializable
        
        with self.assertRaises(FileOperationError):
            self.file_manager._write_json_atomic(test_file, test_data)
        
        # Check that temp file was cleaned up
        temp_file = test_file.with_suffix(".temp")
        self.assertFalse(temp_file.exists())

    def test_read_json_encoding_error(self):
        """Test reading JSON with encoding error."""
        test_file = Path(self.temp_dir) / "test.json"
        
        # Create a file with invalid encoding
        with open(test_file, 'wb') as f:
            f.write(b'\xff\xfe\xfd')  # Invalid UTF-8
        
        with self.assertRaises(FileOperationError):
            self.file_manager._read_json(test_file)

    def test_save_master_keys_error(self):
        """Test saving master keys with error."""
        master_keys = [{"key_id": "key1", "salt": "salt1", "iterations": 100000, "created_at": "2023-01-01T00:00:00Z"}]
        
        # Mock _write_json_atomic to raise an exception
        with patch.object(self.file_manager, '_write_json_atomic', side_effect=FileOperationError("Write failed")):
            with self.assertRaises(FileOperationError):
                self.file_manager.save_master_keys(master_keys)

    def test_save_credentials_index_error(self):
        """Test saving credentials index with error."""
        index = CredentialsIndex()
        
        # Mock _write_json_atomic to raise an exception
        with patch.object(self.file_manager, '_write_json_atomic', side_effect=FileOperationError("Write failed")):
            with self.assertRaises(FileOperationError):
                self.file_manager.save_credentials_index(index)

    def test_save_credential_file_error(self):
        """Test saving credential file with error."""
        credential_file = CredentialFile(
            name="Test Credential",
            key_id="test-key",
            salt="test-salt",
            data="encrypted-data",
            created_at="2023-01-01T00:00:00Z"
        )
        
        # Mock _write_json_atomic to raise an exception
        with patch.object(self.file_manager, '_write_json_atomic', side_effect=FileOperationError("Write failed")):
            with self.assertRaises(FileOperationError):
                self.file_manager.save_credential_file("test-key", credential_file)

    def test_delete_credential_file_error(self):
        """Test deleting credential file with error."""
        credential_path = self.file_manager.data_directory / "test-key.credential.json"
        
        # Create the file
        with open(credential_path, 'w') as f:
            f.write('{"test": "data"}')
        
        # Mock Path.unlink to raise an exception
        with patch.object(Path, 'unlink', side_effect=OSError("Permission denied")):
            with self.assertRaises(FileOperationError):
                self.file_manager.delete_credential_file("test-key")

    def test_backup_files_error(self):
        """Test backing up files with error."""
        # Create a file to backup
        master_keys = [{"key_id": "key1", "salt": "salt1", "iterations": 100000, "created_at": "2023-01-01T00:00:00Z"}]
        self.file_manager.save_master_keys(master_keys)
        
        backup_dir = os.path.join(self.temp_dir, "backup")
        
        # Mock shutil.copy2 to raise an exception
        with patch('shutil.copy2', side_effect=OSError("Copy failed")):
            with self.assertRaises(FileOperationError):
                self.file_manager.backup_files(backup_dir)

    def test_cleanup_expired_backups_logs_errors(self):
        """Test that cleanup_expired_backups logs errors instead of silently ignoring them."""
        # Create a test backup
        backup = RotationBackup(
            backup_id="test-backup",
            rotation_id="test-rotation",
            backup_type="master",
            original_data={"test": "data"},
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
            expires_at=datetime.now(timezone.utc) - timedelta(days=5)  # Expired
        )
        
        # Save the backup
        self.file_manager.save_rotation_backup(backup)
        
        # Mock the delete_rotation_backup method to raise an exception
        with patch.object(self.file_manager, 'delete_rotation_backup', side_effect=OSError("Permission denied")):
            # Run cleanup with error logging
            with self.assertLogs(level=logging.WARNING) as log_context:
                cleaned_count = self.file_manager.cleanup_expired_backups()
            
            # Verify that the error was logged
            log_output = '\n'.join(log_context.output)
            self.assertIn("Failed to delete expired backup test-backup", log_output)
            self.assertIn("Permission denied", log_output)
            
            # Verify that cleanup continued and returned 0 (no successful deletions)
            self.assertEqual(cleaned_count, 0)


if __name__ == "__main__":
    unittest.main() 