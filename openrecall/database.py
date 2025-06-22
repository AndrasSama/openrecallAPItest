"""
Database interaction module for OpenRecall.

This module handles all SQLite database operations, including schema creation,
data insertion, and data retrieval. It uses the `sqlite3` module for
database connectivity and operations. The database stores information
extracted from screenshots, including text content, application context,
and semantic embeddings.
"""
import sqlite3
from collections import namedtuple
import numpy as np
from typing import Any, List, Optional, Tuple # ORIGINAL COMMENT: Any, Tuple not used, but kept for potential future use.

# Import the database path from the application's configuration module.
from openrecall.config import db_path

# ORIGINAL COMMENT: Define the structure of a database entry using namedtuple
# The Entry namedtuple provides a structured way to represent rows from the 'entries' table.
# This makes accessing fields by name (e.g., entry.app) more readable than using indices.
Entry = namedtuple("Entry", ["id", "app", "title", "text", "timestamp", "embedding"])


def create_db() -> None:
    """
    ORIGINAL COMMENT: Creates the SQLite database and the 'entries' table if they don't exist.

    ORIGINAL COMMENT: The table schema includes columns for an auto-incrementing ID, application name,
    ORIGINAL COMMENT: window title, extracted text, timestamp, and text embedding.

    This function connects to the SQLite database file specified by `db_path`.
    It executes SQL commands to create the 'entries' table if it's not already present.
    The 'timestamp' column has a UNIQUE constraint to prevent duplicate entries
    for the same moment in time. An index is also created on the 'timestamp'
    column to optimize lookups based on time.
    """
    try:
        # Establish a connection to the SQLite database.
        # The 'with' statement ensures the connection is properly closed.
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()  # Create a cursor object to execute SQL commands.
            # SQL command to create the 'entries' table.
            # IF NOT EXISTS prevents an error if the table already exists.
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS entries (
                       id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique identifier for each entry
                       app TEXT,                            -- Name of the application in focus
                       title TEXT,                          -- Title of the window in focus
                       text TEXT,                           -- OCR extracted text from the screenshot
                       timestamp INTEGER UNIQUE,            -- Unix timestamp of the screenshot; must be unique
                       embedding BLOB                       -- Stores the NumPy array for text embedding as a binary large object
                   )"""
            )
            # ORIGINAL COMMENT: Add index on timestamp for faster lookups
            # This index helps speed up queries that filter or order by the timestamp column.
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON entries (timestamp)"
            )
            conn.commit()  # Commit the changes to the database.
    except sqlite3.Error as e:
        # Print an error message if any SQLite error occurs during table creation.
        print(f"Database error during table creation: {e}")


def get_all_entries() -> List[Entry]:
    """
    ORIGINAL COMMENT: Retrieves all entries from the database.

    ORIGINAL COMMENT: Returns:
    ORIGINAL COMMENT:     List[Entry]: A list of all entries as Entry namedtuples.
    ORIGINAL COMMENT:                  Returns an empty list if the table is empty or an error occurs.

    This function fetches all rows from the 'entries' table, ordered by timestamp
    in descending order (most recent first). Each row is converted into an 'Entry'
    namedtuple. The 'embedding' BLOB is deserialized back into a NumPy array.
    """
    entries: List[Entry] = []  # Initialize an empty list to store the retrieved entries.
    try:
        with sqlite3.connect(db_path) as conn:
            # ORIGINAL COMMENT: Return rows as dictionary-like objects
            # This allows accessing columns by name (e.g., row['app']) which is more robust to schema changes.
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # SQL query to select all relevant columns from the 'entries' table.
            # Results are ordered by timestamp in descending order.
            cursor.execute("SELECT id, app, title, text, timestamp, embedding FROM entries ORDER BY timestamp DESC")
            results = cursor.fetchall()  # Fetch all rows from the query result.
            for row in results:
                # ORIGINAL COMMENT: Deserialize the embedding blob back into a NumPy array
                # ORIGINAL COMMENT: # Assuming float32, adjust if needed
                # The embedding is stored as bytes (BLOB) and needs to be converted back to a NumPy array.
                # It's crucial that the dtype used here (np.float32) matches the dtype used during serialization in `insert_entry`.
                embedding_blob = row["embedding"]
                if embedding_blob:
                    embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                else:
                    # Handle cases where embedding might be None, though current schema/logic implies it's always present.
                    embedding = np.array([], dtype=np.float32) # Or None, depending on desired handling.

                entries.append(
                    Entry(
                        id=row["id"],
                        app=row["app"],
                        title=row["title"],
                        text=row["text"],
                        timestamp=row["timestamp"],
                        embedding=embedding,
                    )
                )
    except sqlite3.Error as e:
        # Print an error message if any SQLite error occurs during data retrieval.
        print(f"Database error while fetching all entries: {e}")
    return entries


def get_timestamps() -> List[int]:
    """
    ORIGINAL COMMENT: Retrieves all timestamps from the database, ordered descending.

    ORIGINAL COMMENT: Returns:
    ORIGINAL COMMENT:     List[int]: A list of all timestamps.
    ORIGINAL COMMENT:                Returns an empty list if the table is empty or an error occurs.

    This function specifically fetches only the 'timestamp' column from all entries,
    ordered by timestamp in descending order.
    """
    timestamps: List[int] = []  # Initialize an empty list for timestamps.
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # ORIGINAL COMMENT: Use the index for potentially faster retrieval
            # Query to select timestamps, ordered to get the most recent ones first.
            cursor.execute("SELECT timestamp FROM entries ORDER BY timestamp DESC")
            results = cursor.fetchall()  # Fetch all timestamp rows.
            # Extract the timestamp value from each row (results are tuples).
            timestamps = [result[0] for result in results]
    except sqlite3.Error as e:
        # Print an error message if any SQLite error occurs.
        print(f"Database error while fetching timestamps: {e}")
    return timestamps


def insert_entry(
    text: str, timestamp: int, embedding: np.ndarray, app: str, title: str
) -> Optional[int]:
    """
    ORIGINAL COMMENT: Inserts a new entry into the database.

    ORIGINAL COMMENT: Args:
    ORIGINAL COMMENT:     text (str): The extracted text content.
    ORIGINAL COMMENT:     timestamp (int): The Unix timestamp of the screenshot.
    ORIGINAL COMMENT:     embedding (np.ndarray): The embedding vector for the text.
    ORIGINAL COMMENT:     app (str): The name of the active application.
    ORIGINAL COMMENT:     title (str): The title of the active window.

    ORIGINAL COMMENT: Returns:
    ORIGINAL COMMENT:     Optional[int]: The ID of the newly inserted row, or None if insertion fails.
    ORIGINAL COMMENT:                    Prints an error message to stderr on failure.

    This function serializes the NumPy embedding array into bytes and then inserts
    the provided data as a new row into the 'entries' table.
    The `ON CONFLICT(timestamp) DO NOTHING` clause ensures that if an entry
    with the same timestamp already exists, the insertion is skipped, maintaining
    the uniqueness of timestamps.
    """
    # ORIGINAL COMMENT: # Ensure consistent dtype
    # Convert the NumPy embedding array to a specific data type (float32) and then to bytes for BLOB storage.
    # This consistency is vital for correct deserialization later.
    embedding_bytes: bytes = embedding.astype(np.float32).tobytes()
    last_row_id: Optional[int] = None  # Initialize variable to store the ID of the inserted row.
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # SQL command to insert a new row.
            # Parameters are passed as a tuple to prevent SQL injection vulnerabilities.
            # `ON CONFLICT(timestamp) DO NOTHING` handles cases where a record with the same timestamp already exists.
            cursor.execute(
                """INSERT INTO entries (text, timestamp, embedding, app, title)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(timestamp) DO NOTHING""", # ORIGINAL COMMENT: Avoid duplicates based on timestamp
                (text, timestamp, embedding_bytes, app, title),
            )
            conn.commit()  # Commit the transaction.
            # ORIGINAL COMMENT: # Check if insert actually happened
            # If rowcount is greater than 0, it means a new row was inserted (not skipped due to conflict).
            if cursor.rowcount > 0:
                last_row_id = cursor.lastrowid  # Get the ID of the newly inserted row.
            # ORIGINAL COMMENT: # else:
                # ORIGINAL COMMENT: # Optionally log that a duplicate timestamp was encountered
                # ORIGINAL COMMENT: # print(f"Skipped inserting entry with duplicate timestamp: {timestamp}")

    except sqlite3.Error as e:
        # ORIGINAL COMMENT: # More specific error handling can be added (e.g., IntegrityError for UNIQUE constraint)
        # Print an error message if any SQLite error occurs during insertion.
        print(f"Database error during insertion: {e}")
    return last_row_id
