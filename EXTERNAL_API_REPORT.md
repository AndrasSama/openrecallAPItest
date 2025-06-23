# OpenRecall - External API & Configuration Report

This document outlines the externally accessible variables, functions, classes, configuration points, and API endpoints for the `openrecall` package.

## General Package Structure

The `openrecall` package does not define an `__all__` variable in its `openrecall/__init__.py` file. Therefore, its public API is effectively composed of the importable members (functions, classes, variables) from its various submodules. Users are expected to import directly from these submodules (e.g., `from openrecall.config import appdata_folder`, `from openrecall.app import app`).

## 1. `openrecall.config`

This module handles application configuration, primarily related to storage paths and command-line arguments.

**Configuration Mechanisms:**

*   **Command-Line Arguments:**
    *   `--storage-path` (str, default: `None`): Allows users to specify a custom directory for all application data. If not provided, a default OS-specific path is determined.
    *   `--primary-monitor-only` (bool, default: `False`): If this flag is present, only the primary monitor's screen is recorded.
*   **Environment Variables (Implicit):**
    *   `APPDATA` (Windows only): Used by `get_appdata_folder()` to determine the default storage location if `--storage-path` is not specified. An `EnvironmentError` is raised if `APPDATA` is not set under these conditions.

**Key Exported Variables (derived from configuration):**

These variables are set based on the external configurations and are then imported by other modules.
*   `appdata_folder` (str): The root directory for application data.
*   `db_path` (str): The full path to the SQLite database file (`recall.db`).
*   `screenshots_path` (str): The full path to the directory where screenshots are stored.

**Functions (primarily internal but define configuration logic):**
*   `get_appdata_folder(app_name="openrecall") -> str`: Determines the OS-specific application data folder. While callable, its main role is internal to setting up the above path variables.

## 2. `openrecall.database`

This module provides the data persistence layer.

**Public Functions (Data Access API):**

*   `create_db() -> None`: Initializes the database and creates necessary tables/indexes. Typically called at application startup.
*   `insert_entry(text: str, timestamp: int, embedding: np.ndarray, app: str, title: str) -> Optional[int]`: Inserts a new data record into the database. (Note: `screenshot.py` calls this with an additional `filename` argument, which is not in this module's current definition, suggesting a potential area for future synchronization).
*   `get_all_entries() -> List[Entry]`: Retrieves all entries, ordered by timestamp (descending).
*   `get_timestamps() -> List[int]`: Retrieves all unique timestamps, ordered by timestamp (descending).

**Public Data Structures:**

*   `Entry` (namedtuple): `namedtuple("Entry", ["id", "app", "title", "text", "timestamp", "embedding"])`. This structure is used for records returned by `get_all_entries()`.

## 3. `openrecall.nlp`

Handles Natural Language Processing tasks (embeddings and similarity).

**Public Functions:**

*   `get_embedding(text: str) -> np.ndarray`: Generates a numerical embedding for the input text using a pre-loaded SentenceTransformer model.
*   `cosine_similarity(a: np.ndarray, b: np.ndarray) -> float`: Calculates the cosine similarity between two embedding vectors.

**Informational Constants (defining module behavior):**

*   `MODEL_NAME: str = "all-MiniLM-L6-v2"`: The specific SentenceTransformer model used.
*   `EMBEDDING_DIM: int = 384`: The dimension of the embeddings produced by the model.

**Internal Global State with External Impact:**
*   `model: Optional[SentenceTransformer]`: The loaded NLP model. Its successful loading is critical for `get_embedding`. Failures are logged, and `get_embedding` returns a zero vector if the model is not loaded.

## 4. `openrecall.ocr`

Responsible for Optical Character Recognition.

**Public Functions:**

*   `extract_text_from_image(image: any) -> str`: Takes an image (NumPy array or PIL Image) and returns the extracted text as a string.

**Internal Global State with External Impact:**
*   `ocr: ocr_predictor`: The loaded `doctr` OCR model. Its successful initialization is critical for `extract_text_from_image`.

## 5. `openrecall.screenshot`

Manages screenshot capture and processing.

**Main Controlling Function / Entry Point:**

*   `record_screenshots_thread() -> None` (Primary version): This function, when run in a thread, continuously captures, processes, and stores screen data. It's the main entry point for the application's background recording task, started by `app.py`.

**Potentially Usable Public Helper Functions:**

While primarily used internally by `record_screenshots_thread`, these are accessible:
*   `take_screenshots() -> List[np.ndarray]`: Captures screenshots from monitors.
*   `is_similar(img1: np.ndarray, img2: np.ndarray, similarity_threshold: float = 0.9) -> bool`: Checks image similarity using MSSIM.
*   `mean_structured_similarity_index(img1: np.ndarray, img2: np.ndarray, L: int = 255) -> float`: Calculates the MSSIM score.

## 6. `openrecall.utils`

Contains general-purpose utility functions.

**Public Utility Functions:**

*   `human_readable_time(timestamp: int) -> str`: Converts Unix timestamp to relative time string (e.g., "5 minutes ago").
*   `timestamp_to_human_readable(timestamp: int) -> str`: Converts Unix timestamp to absolute "YYYY-MM-DD HH:MM:SS" string.
*   `get_active_app_name() -> str`: Returns the active application name (platform-agnostic).
*   `get_active_window_title() -> str`: Returns the active window title (platform-agnostic).
*   `is_user_active() -> bool`: Checks if the user is currently active (platform-agnostic).

*(Note: This module also contains platform-specific helper functions (e.g., `get_active_app_name_osx`), which are technically public but primarily abstracted by the generic functions listed above. Their direct use is less common.)*

## 7. `openrecall.app`

The main Flask web application module.

**Primary External Interfaces:**

*   **WSGI Application Object:**
    *   `app` (Flask instance): The WSGI application object used by WSGI servers (e.g., Gunicorn, or Flask's dev server) to run the web app.
*   **HTTP API Endpoints:**
    *   `GET /`: Serves the main timeline HTML page.
    *   `GET /search?q=<query>`: Performs a search and returns an HTML page with results.
        *   Parameter: `q` (string) - The search term.
    *   `GET /static/<filename>`: Serves static files (primarily images).
        *   Parameter: `filename` (string) - The name of the file.

**Application Execution (when run as `__main__`):**
*   The script initializes the database (`create_db()`).
*   Starts the `record_screenshots_thread()` in a background thread.
*   Runs the Flask development server on `http://localhost:8082`. The port `8082` is the default external access point for the web service.

## Summary of External Interaction Points

*   **Configuration:** Via command-line arguments (`--storage-path`, `--primary-monitor-only`) and potentially the `APPDATA` environment variable (Windows).
*   **Programmatic Execution:**
    *   The `record_screenshots_thread()` in `openrecall.screenshot` can be imported and started in a thread to begin data capture.
    *   Individual utility functions from `openrecall.utils`, `openrecall.nlp`, `openrecall.ocr`, and `openrecall.database` can be imported and used if direct access to their specific functionalities is needed.
*   **Web Service Access (when `app.py` is run):**
    *   HTTP GET requests to `/`, `/search`, and `/static/` endpoints.
    *   The service runs on `http://localhost:8082` by default.
*   **Data Structures:**
    *   The `Entry` namedtuple from `openrecall.database` defines the structure of data records fetched via `get_all_entries()`.
    *   Embeddings are returned as NumPy arrays by `openrecall.nlp.get_embedding()`.
    *   Screenshots are handled as NumPy arrays by `openrecall.screenshot.take_screenshots()`.

This report should provide a good overview of how to interact with and configure the `openrecall` package from an external perspective.
