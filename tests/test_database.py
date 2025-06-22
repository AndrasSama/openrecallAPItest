"""
Tests for the `openrecall.database` module.

This test suite uses the `unittest` framework and `unittest.mock.patch` to
thoroughly test database operations. A key feature of this suite is its setup
of a temporary, isolated database for each test run. This is achieved by:
1.  Modifying `sys.path` temporarily to allow imports from the parent `openrecall` directory.
    (Note: This is a common workaround for running tests directly but might be
    better handled by test runner configurations or project structure in larger projects).
2.  Creating a temporary file using `tempfile.NamedTemporaryFile`.
3.  Patching `openrecall.config.db_path` *before* importing database functions. This ensures
    that all functions within `openrecall.database` (and any modules they import which
    might subsequently import `db_path` from config) use this temporary database path.
4.  The `TestDatabase` class uses `setUpClass` to create the database schema once and
    `tearDownClass` to remove the temporary database file. `setUp` and `tearDown`
    methods handle per-test database connection and cleanup (clearing entries).
"""
import unittest
import sqlite3
import os
import tempfile # For creating temporary files/directories.
import time
import numpy as np
from unittest.mock import patch # For mocking objects, especially `db_path`.

# ORIGINAL COMMENT: Temporarily adjust path to import from openrecall
# This allows running the test script directly while still being able to import
# modules from the parent `openrecall` package.
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ORIGINAL COMMENT: Now import from openrecall.database, mocking db_path *before* the import
# ORIGINAL COMMENT: Create a temporary file path that will be used by the mock
# Create a temporary file that will serve as the SQLite database for testing.
# `delete=False` is important so the file isn't deleted when closed, allowing us to use its name.
temp_db_file = tempfile.NamedTemporaryFile(delete=False)
mock_db_path = temp_db_file.name # Get the path to the temporary file.
# ORIGINAL COMMENT: temp_db_file.close() # Close the file handle, but the file persists because delete=False
temp_db_file.close()

# Patch `openrecall.config.db_path` with `mock_db_path`.
# This context manager ensures that within this `with` block, any reference
# to `openrecall.config.db_path` will use `mock_db_path`.
with patch('openrecall.config.db_path', mock_db_path):
    # Imports from `openrecall.database` are done *after* `db_path` is patched.
    from openrecall.database import (
        create_db,
        insert_entry,
        get_all_entries,
        get_timestamps,
        Entry, # The namedtuple for database entries.
    )
    # ORIGINAL COMMENT: Also patch db_path within the database module itself if it was imported directly there
    # This is a safety measure: if `openrecall.database` itself imported `db_path` like
    # `from openrecall.config import db_path` (it does), the above patch might not affect
    # the `db_path` already imported into the `openrecall.database` namespace directly.
    # So, we explicitly set it in the already imported module's namespace too.
    import openrecall.database
    openrecall.database.db_path = mock_db_path


class TestDatabase(unittest.TestCase):
    """
    Test case for database operations defined in `openrecall.database`.
    Uses a temporary SQLite database file that is created before tests
    and removed after.
    """

    @classmethod
    def setUpClass(cls):
        # ORIGINAL COMMENT: """Set up a temporary database file for all tests in this class."""
        """
        Set up a temporary database file once for all tests in this class.
        The database schema (`entries` table and index) is also created here.
        """
        # ORIGINAL COMMENT: The database path is already patched by the module-level patch
        cls.db_path = mock_db_path # Store the path for potential direct use, though functions use patched one.
        # ORIGINAL COMMENT: Ensure the database and table are created once
        create_db() # Create the 'entries' table in the temporary database.

    @classmethod
    def tearDownClass(cls):
        # ORIGINAL COMMENT: """Remove the temporary database file after all tests."""
        """
        Remove the temporary database file after all tests in this class are run.
        Also cleans up the `sys.path` modification.
        """
        # ORIGINAL COMMENT: Try closing connection if any test left it open (though setUp/tearDown should handle this)
        try:
            # This is a safeguard in case a test method incorrectly leaves a connection open.
            if hasattr(cls, 'conn') and cls.conn:
                cls.conn.close()
        except Exception:
            # ORIGINAL COMMENT: pass # Ignore errors during cleanup
            pass
        os.remove(cls.db_path) # Delete the temporary database file.
        # ORIGINAL COMMENT: Clean up sys.path modification
        sys.path.pop(0) # Remove the path added at the beginning.


    def setUp(self):
        # ORIGINAL COMMENT: """Connect to the database and clear entries before each test."""
        """
        Connect to the temporary database and clear all entries from the 'entries'
        table before each individual test method is run. This ensures test isolation.
        """
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM entries") # Clear out data from previous tests.
        self.conn.commit()
        # ORIGINAL COMMENT: No need to close here, will be handled by tearDown or next setUp potentially

    def tearDown(self):
        # ORIGINAL COMMENT: """Close the database connection after each test."""
        """
        Close the database connection after each test method completes.
        """
        if self.conn:
            self.conn.close()

    def test_create_db(self):
        # ORIGINAL COMMENT: """Test if create_db creates the table and index."""
        """
        Tests if the `create_db` function correctly creates the 'entries' table
        and the 'idx_timestamp' index.
        """
        # ORIGINAL COMMENT: Check if table exists
        cursor = self.conn.cursor()
        # Query sqlite_master table for the 'entries' table.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        result = cursor.fetchone()
        self.assertIsNotNone(result, "The 'entries' table should exist.")
        self.assertEqual(result[0], 'entries')

        # ORIGINAL COMMENT: Check if index exists
        # Query sqlite_master for the 'idx_timestamp' index.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_timestamp'")
        result = cursor.fetchone()
        self.assertIsNotNone(result, "The 'idx_timestamp' index should exist.")
        self.assertEqual(result[0], 'idx_timestamp')

    def test_02_insert_entry(self): # Prefix "02_" suggests ordering, though unittest doesn't guarantee by default.
        # ORIGINAL COMMENT: """Test inserting a single entry."""
        """
        Tests the insertion of a single entry into the database and verifies
        that all fields, including the deserialized embedding, are stored correctly.
        """
        ts = int(time.time()) # Current timestamp for the entry.
        embedding_data = np.array([0.1, 0.2, 0.3], dtype=np.float32) # Sample embedding.
        # Call insert_entry with test data.
        inserted_id = insert_entry("Test text", ts, embedding_data, "TestApp", "TestTitle")

        self.assertIsNotNone(inserted_id, "insert_entry should return an ID for a new entry.")
        self.assertIsInstance(inserted_id, int, "The returned ID should be an integer.")

        # ORIGINAL COMMENT: Verify the entry exists in the DB
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entries WHERE id = ?", (inserted_id,))
        result = cursor.fetchone() # Fetch the inserted row.
        self.assertIsNotNone(result, "The entry should be found in the database by its ID.")

        # ORIGINAL COMMENT: (id, app, title, text, timestamp, embedding_blob)
        # Verify each field of the retrieved row.
        self.assertEqual(result[1], "TestApp", "Application name mismatch.")
        self.assertEqual(result[2], "TestTitle", "Window title mismatch.")
        self.assertEqual(result[3], "Test text", "Extracted text mismatch.")
        self.assertEqual(result[4], ts, "Timestamp mismatch.")
        # Deserialize the embedding BLOB and compare with the original.
        retrieved_embedding = np.frombuffer(result[5], dtype=np.float32)
        np.testing.assert_array_almost_equal(retrieved_embedding, embedding_data, decimal=5, err_msg="Embedding data mismatch.")

    def test_insert_duplicate_timestamp(self):
        # ORIGINAL COMMENT: """Test inserting an entry with a duplicate timestamp (should be ignored)."""
        """
        Tests that inserting an entry with a timestamp that already exists in the
        database is correctly ignored (due to `ON CONFLICT(timestamp) DO NOTHING`).
        Verifies that no new entry is added and the original entry is preserved.
        """
        ts = int(time.time())
        embedding1 = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        embedding2 = np.array([0.4, 0.5, 0.6], dtype=np.float32) # Different content for the duplicate.

        # Insert the first entry.
        id1 = insert_entry("First text", ts, embedding1, "App1", "Title1")
        self.assertIsNotNone(id1, "First entry should be inserted successfully.")

        # ORIGINAL COMMENT: Try inserting another entry with the same timestamp
        # Attempt to insert a second entry with the exact same timestamp.
        id2 = insert_entry("Second text", ts, embedding2, "App2", "Title2")
        # `insert_entry` should return None if the insertion was skipped due to conflict.
        self.assertIsNone(id2, "Inserting an entry with a duplicate timestamp should return None.")

        # ORIGINAL COMMENT: Verify only the first entry exists
        cursor = self.conn.cursor()
        # Count entries with the given timestamp; should still be 1.
        cursor.execute("SELECT COUNT(*) FROM entries WHERE timestamp = ?", (ts,))
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1, "There should only be one entry for the given timestamp.")

        # Verify that the content of the existing entry is from the first insertion.
        cursor.execute("SELECT text FROM entries WHERE timestamp = ?", (ts,))
        text_in_db = cursor.fetchone()[0]
        # ORIGINAL COMMENT: self.assertEqual(text, "First text") # Ensure the first one was kept
        self.assertEqual(text_in_db, "First text", "The original entry's text should be preserved.")

    def test_get_all_entries_empty(self):
        # ORIGINAL COMMENT: """Test getting entries from an empty database."""
        """
        Tests `get_all_entries` when the database contains no entries.
        It should return an empty list.
        """
        entries = get_all_entries()
        self.assertEqual(entries, [], "get_all_entries on an empty DB should return an empty list.")

    def test_get_all_entries_multiple(self):
        # ORIGINAL COMMENT: """Test retrieving multiple entries."""
        """
        Tests `get_all_entries` with multiple entries, ensuring they are retrieved
        correctly and ordered by timestamp in descending order (most recent first).
        """
        ts1 = int(time.time())
        ts2 = ts1 + 10 # More recent.
        ts3 = ts1 - 10 # Older. Ensure ordering works
        emb1 = np.array([0.1] * 5, dtype=np.float32)
        emb2 = np.array([0.2] * 5, dtype=np.float32)
        emb3 = np.array([0.3] * 5, dtype=np.float32)

        # Insert entries in a non-chronological order to test sorting.
        insert_entry("Text 1", ts1, emb1, "App1", "Title1")
        insert_entry("Text 2", ts2, emb2, "App2", "Title2") # Most recent.
        insert_entry("Text 3", ts3, emb3, "App3", "Title3") # Oldest.

        entries = get_all_entries()
        self.assertEqual(len(entries), 3, "Should retrieve all three inserted entries.")

        # ORIGINAL COMMENT: Entries should be ordered by timestamp DESC
        # Verify the first entry (most recent: ts2).
        self.assertEqual(entries[0].timestamp, ts2)
        self.assertEqual(entries[0].text, "Text 2")
        self.assertEqual(entries[0].app, "App2")
        self.assertEqual(entries[0].title, "Title2")
        np.testing.assert_array_almost_equal(entries[0].embedding, emb2, decimal=5)
        self.assertIsInstance(entries[0].id, int)

        # Verify the second entry (middle: ts1).
        self.assertEqual(entries[1].timestamp, ts1)
        self.assertEqual(entries[1].text, "Text 1")
        np.testing.assert_array_almost_equal(entries[1].embedding, emb1, decimal=5)

        # Verify the third entry (oldest: ts3).
        self.assertEqual(entries[2].timestamp, ts3)
        self.assertEqual(entries[2].text, "Text 3")
        np.testing.assert_array_almost_equal(entries[2].embedding, emb3, decimal=5)

    def test_get_timestamps_empty(self):
        # ORIGINAL COMMENT: """Test getting timestamps from an empty database."""
        """
        Tests `get_timestamps` when the database is empty.
        It should return an empty list.
        """
        timestamps = get_timestamps()
        self.assertEqual(timestamps, [], "get_timestamps on an empty DB should return an empty list.")

    def test_get_timestamps_multiple(self):
        # ORIGINAL COMMENT: """Test retrieving multiple timestamps."""
        """
        Tests `get_timestamps` with multiple entries, ensuring timestamps are
        retrieved correctly and ordered in descending order.
        """
        ts1 = int(time.time())
        ts2 = ts1 + 10 # Most recent.
        ts3 = ts1 - 10 # Oldest.
        # ORIGINAL COMMENT: emb = np.array([0.1] * 5, dtype=np.float32) # Embedding content doesn't matter here
        emb = np.array([0.1] * 5, dtype=np.float32)

        insert_entry("T1", ts1, emb, "A1", "T1")
        insert_entry("T2", ts2, emb, "A2", "T2")
        insert_entry("T3", ts3, emb, "A3", "T3")

        timestamps = get_timestamps()
        self.assertEqual(len(timestamps), 3, "Should retrieve all three timestamps.")
        # ORIGINAL COMMENT: Timestamps should be ordered DESC
        self.assertEqual(timestamps, [ts2, ts1, ts3], "Timestamps are not in descending order.")


if __name__ == '__main__':
    # This allows running the tests directly using `python tests/test_database.py`.
    unittest.main()