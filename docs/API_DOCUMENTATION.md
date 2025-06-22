# OpenRecall API Documentation

This document outlines the API endpoints for the OpenRecall application.

## Web Server

The local web server is handled by a Flask application located in `openrecall/app.py`.

## Endpoints

### 1. Root / Timeline

*   **HTTP Method:** `GET`
*   **Endpoint:** `/`
*   **Description:** Displays the main timeline view, showing recorded screenshots.
*   **Parameters:** None
*   **Expected Response:** HTML page. The content includes a slider to navigate through timestamps and an image container to display the screenshot for the selected timestamp. If no screenshots are recorded yet, it displays an "Nothing recorded yet" message.

### 2. Search

*   **HTTP Method:** `GET`
*   **Endpoint:** `/search`
*   **Description:** Performs a search based on a query string and displays the results.
*   **Parameters:**
    *   `q` (string, required): The search query.
*   **Expected Response:** HTML page. The page displays a grid of images that are relevant to the search query. Each image is a link that opens a modal view of the full-size image.

    *Example Request:* `GET /search?q=python+code`

    *Response Structure (Conceptual HTML):*
    ```html
    <!-- ... (base template HTML) ... -->
    <div class="container">
        <div class="row">
            <!-- For each search result entry: -->
            <div class="col-md-3 mb-4">
                <div class="card">
                    <a href="#" data-toggle="modal" data-target="#modal-INDEX">
                        <img src="/static/TIMESTAMP.webp" alt="Image" class="card-img-top">
                    </a>
                </div>
            </div>
            <!-- Modal for the image -->
            <div class="modal fade" id="modal-INDEX" ...>
                <!-- ... modal content with full image ... -->
            </div>
            <!-- ... (end for each) ... -->
        </div>
    </div>
    <!-- ... (base template HTML) ... -->
    ```

### 3. Static Image Access

*   **HTTP Method:** `GET`
*   **Endpoint:** `/static/<filename>`
*   **Description:** Serves static image files (screenshots).
*   **Parameters:**
    *   `filename` (string, required): The name of the image file (e.g., `TIMESTAMP.webp`).
*   **Expected Response:** The image file (e.g., content type `image/webp`).

    *Example Request:* `GET /static/1678886400.webp`
