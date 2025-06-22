"""
Main Flask web application for OpenRecall.

This module sets up and runs the Flask application, defining routes for the user
interface, including a timeline view of recorded screenshots and a search
functionality. It also handles serving static image files.

A notable characteristic of this application is its use of embedded HTML templates
within this Python file, loaded via a custom Jinja2 string loader, rather than
relying on separate HTML files in a 'templates' directory.

The application also initializes the database and starts the background thread
for continuous screenshot recording when run directly.
"""
from threading import Thread # For running the screenshot recorder in the background.

import numpy as np
from flask import Flask, render_template_string, request, send_from_directory
from jinja2 import BaseLoader # For custom template loading.

# Importing various components from the OpenRecall application package.
from openrecall.config import appdata_folder, screenshots_path
from openrecall.database import create_db, get_all_entries, get_timestamps
from openrecall.nlp import cosine_similarity, get_embedding
from openrecall.screenshot import record_screenshots_thread
from openrecall.utils import human_readable_time, timestamp_to_human_readable

# Initialize the Flask application.
app = Flask(__name__)

# Register custom Jinja2 filters for use in templates.
# These filters provide human-readable time formatting.
app.jinja_env.filters["human_readable_time"] = human_readable_time
app.jinja_env.filters["timestamp_to_human_readable"] = timestamp_to_human_readable

# Define the base HTML template as a Python string.
# This template includes Bootstrap for styling and provides a common layout
# (navigation bar with search) for other views.
base_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenRecall</title>
  <!-- Bootstrap CSS from CDN -->
  <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
  <!-- Bootstrap Icons from CDN -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.3.0/font/bootstrap-icons.css">
  <style>
    /* Basic styling for slider and image display */
    .slider-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
    }
    .slider {
      width: 80%; /* Slider width */
    }
    .slider-value {
      margin-top: 10px;
      font-size: 1.2em; /* Displayed timestamp value */
    }
    .image-container {
      margin-top: 20px;
      text-align: center; /* Center the image */
    }
    .image-container img {
      max-width: 100%; /* Responsive image */
      height: auto;
    }
  </style>
</head>
<body>
<nav class="navbar navbar-light bg-light">
  <div class="container">
    <!-- Search form in the navigation bar -->
    <form class="form-inline my-2 my-lg-0 w-100 d-flex" action="/search" method="get">
      <input class="form-control flex-grow-1 mr-sm-2" type="search" name="q" placeholder="Search" aria-label="Search">
      <button class="btn btn-outline-secondary my-2 my-sm-0" type="submit">
        <i class="bi bi-search"></i> <!-- Search icon -->
      </button>
    </form>
  </div>
</nav>
{% block content %}
<!-- Placeholder for page-specific content -->
{% endblock %}

  <!-- Bootstrap and jQuery JS from CDNs for interactivity (e.g., modals) -->
  <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.3/dist/umd/popper.min.js"></script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
  
</body>
</html>
"""


class StringLoader(BaseLoader):
    """
    A custom Jinja2 template loader that loads templates from a predefined string.
    In this application, it's used to load the `base_template` defined above.
    """
    def get_source(self, environment, template):
        """
        Retrieves the source for a template.
        If the template name is "base_template", it returns the `base_template` string.
        """
        if template == "base_template":
            # Returns the template string, its filename (None as it's from a string),
            # and a callable that returns True if the template is up-to-date (always True for string templates).
            return base_template, None, lambda: True
        # If the template name is not "base_template", it cannot be found by this loader.
        return None, None, None


# Set the custom string loader as the Jinja2 environment's loader.
app.jinja_env.loader = StringLoader()


@app.route("/")
def timeline():
    """
    Route for the main timeline view (homepage).

    Displays a timeline of recorded screenshots. Users can navigate through
    screenshots using a slider. If no screenshots are available, a message
    indicating this is shown.
    """
    # ORIGINAL COMMENT: connect to db
    # Fetch all unique timestamps from the database, ordered most recent first.
    timestamps = get_timestamps()

    # Render the timeline view using an embedded Jinja2 template string.
    # This template extends "base_template".
    return render_template_string(
        """
{% extends "base_template" %} {# Inherits from the base_template string #}
{% block content %} {# Fills the content block of the base template #}
{% if timestamps|length > 0 %} {# Check if there are any recorded timestamps #}
  <div class="container">
    <div class="slider-container">
      <!-- Range slider to navigate through timestamps -->
      <input type="range" class="slider custom-range" id="discreteSlider"
             min="0" max="{{timestamps|length - 1}}" step="1"
             value="{{timestamps|length - 1}}"> {# Initialize slider to the most recent timestamp #}
      <!-- Div to display the human-readable format of the selected timestamp -->
      <div class="slider-value" id="sliderValue">{{timestamps[0] | timestamp_to_human_readable }}</div>
    </div>
    <div class="image-container">
      <!-- Image element to display the screenshot for the selected timestamp -->
      <img id="timestampImage" src="/static/{{timestamps[0]}}.webp" alt="Image for timestamp">
    </div>
  </div>
  <script>
    // Inline JavaScript for slider interactivity.
    const timestamps = {{ timestamps|tojson }}; // Pass timestamps from Python to JavaScript.
    const slider = document.getElementById('discreteSlider');
    const sliderValue = document.getElementById('sliderValue');
    const timestampImage = document.getElementById('timestampImage');

    // Event listener for slider input changes.
    slider.addEventListener('input', function() {
      // Slider value is 0 for oldest, (length-1) for newest. Timestamps array is newest first.
      const reversedIndex = timestamps.length - 1 - slider.value;
      const timestamp = timestamps[reversedIndex];
      // Update the displayed timestamp value and the image source.
      sliderValue.textContent = new Date(timestamp * 1000).toLocaleString();  // ORIGINAL COMMENT: Convert to human-readable format
      timestampImage.src = `/static/${timestamp}.webp`; // Assumes image filenames match timestamps.
    });

    // ORIGINAL COMMENT: Initialize the slider with a default value (most recent screenshot).
    slider.value = timestamps.length - 1;
    sliderValue.textContent = new Date(timestamps[0] * 1000).toLocaleString();  // ORIGINAL COMMENT: Convert to human-readable format
    timestampImage.src = `/static/${timestamps[0]}.webp`;
  </script>
{% else %} {# If no timestamps are recorded #}
  <div class="container">
      <div class="alert alert-info" role="alert">
          Nothing recorded yet, wait a few seconds.
      </div>
  </div>
{% endif %}
{% endblock %}
""",
        timestamps=timestamps, # Pass the timestamps list to the template.
    )


@app.route("/search")
def search():
    """
    Route for the search functionality.

    Accepts a query parameter 'q'. It fetches all entries from the database,
    calculates the cosine similarity between the query's embedding and each
    entry's embedding, and then displays the results sorted by relevance.
    Results are shown as a grid of images, each linking to a modal for a larger view.
    """
    q = request.args.get("q") # Get the search query from URL parameters (e.g., /search?q=myquery).

    if not q or q.isspace(): # Handle empty or whitespace-only queries
        # Optionally, redirect to timeline or show a message. For now, will proceed and likely show no results.
        # Or, could return a specific template:
        # return render_template_string("...", message="Please enter a search term.")
        pass

    entries = get_all_entries() # Retrieve all stored entries.

    # Check if there are any entries to search through.
    if not entries:
        return render_template_string("""
{% extends "base_template" %}
{% block content %}
    <div class="container">
        <div class="alert alert-info" role="alert">
            No entries to search. Start recording data.
        </div>
    </div>
{% endblock %}
""", entries=[]) # Pass empty list

    # Deserialize embeddings from BLOB to NumPy arrays.
    # POTENTIAL ISSUE: dtype=np.float64 used here for deserialization.
    # This might be inconsistent if embeddings were stored as np.float32 (common for sentence transformers).
    # Ensure consistency with database.py (serialization) and nlp.py (embedding generation).
    # If stored as float32, using float64 here will misinterpret the bytes.
    try:
        # Assuming entry.embedding is bytes.
        embeddings = [np.frombuffer(entry.embedding, dtype=np.float32) for entry in entries if entry.embedding is not None]
        # Filter out entries where embedding was None or could not be processed
        valid_entries = [entry for entry in entries if entry.embedding is not None]
        if not valid_entries or not embeddings: # If no valid embeddings after filtering
             return render_template_string("""
{% extends "base_template" %}
{% block content %}
    <div class="container">
        <p>No searchable content found or embeddings are missing/corrupted.</p>
    </div>
{% endblock %}
""", entries=[])
    except Exception as e:
        print(f"Error deserializing embeddings: {e}") # Log error
        # Render a page indicating an error with embeddings.
        return render_template_string("""
{% extends "base_template" %}
{% block content %}
    <div class="container">
        <p>Error processing data for search. Embeddings might be corrupted.</p>
    </div>
{% endblock %}
""", entries=[])


    query_embedding = get_embedding(q if q else "") # Get embedding for the search query.

    # Calculate cosine similarities between the query embedding and all entry embeddings.
    similarities = [cosine_similarity(query_embedding, emb) for emb in embeddings]

    # Get indices that would sort the similarities in descending order.
    indices = np.argsort(similarities)[::-1]
    # Sort the original valid_entries based on these similarity indices.
    sorted_entries = [valid_entries[i] for i in indices]

    # Render the search results page using an embedded Jinja2 template string.
    return render_template_string(
        """
{% extends "base_template" %} {# Inherits from base_template #}
{% block content %}
    <div class="container">
        <div class="row">
            {% if entries %}
                {% for entry in entries %} {# Iterate through sorted search results #}
                    <div class="col-md-3 mb-4"> {# Bootstrap column for grid layout #}
                        <div class="card">
                            <!-- Link to trigger modal display for the image -->
                            <a href="#" data-toggle="modal" data-target="#modal-{{ loop.index0 }}">
                                <!-- Display screenshot thumbnail -->
                                <img src="/static/{{ entry.filename if entry.filename else entry.timestamp ~ '.webp' }}" alt="Screenshot for {{ entry.text|truncate(30) }}" class="card-img-top">
                            </a>
                        </div>
                    </div>
                    <!-- Modal definition for displaying the full-size image -->
                    <div class="modal fade" id="modal-{{ loop.index0 }}" tabindex="-1" role="dialog" aria-labelledby="modalLabel-{{ loop.index0 }}" aria-hidden="true">
                        <div class="modal-dialog modal-xl" role="document" style="max-width: none; width: 100vw; height: 100vh; padding: 20px;">
                            <div class="modal-content" style="height: calc(100vh - 40px); width: calc(100vw - 40px); padding: 0;">
                                <div class="modal-body" style="padding: 0;">
                                    <!-- Full-size image within the modal -->
                                    <img src="/static/{{ entry.filename if entry.filename else entry.timestamp ~ '.webp' }}" alt="Full screenshot for {{ entry.text|truncate(30) }}" style="width: 100%; height: 100%; object-fit: contain; margin: 0 auto;">
                                </div>
                            </div>
                        </div>
                    </div>
                {% endfor %}
            {% else %}
                <div class="col">
                    <p>No results found for your query: "{{ request.args.get('q') }}"</p>
                </div>
            {% endif %}
        </div>
    </div>
{% endblock %}
""",
        entries=sorted_entries, # Pass sorted entries to the template.
        request=request # Pass the request object to access query params in template if needed
    )


@app.route("/static/<filename>")
def serve_image(filename: str):
    """
    Serves static image files (e.g., screenshots) from the configured screenshots directory.

    Args:
        filename (str): The name of the file to serve.

    Returns:
        Response: The file content or a 404 error if not found.
    """
    # Uses Flask's send_from_directory to securely serve files.
    return send_from_directory(screenshots_path, filename)


# This block executes if the script is run directly (e.g., `python app.py`).
if __name__ == "__main__":
    create_db() # Ensure the database and necessary tables are created.

    print(f"Appdata folder: {appdata_folder}") # Log the application data folder path.

    # ORIGINAL COMMENT: Start the thread to record screenshots
    # Initialize and start the background thread for screenshot recording.
    # This allows the web server to run concurrently with the recording process.
    print("Starting screenshot recording thread...")
    screenshot_thread = Thread(target=record_screenshots_thread, daemon=True) # daemon=True allows main program to exit even if thread is running
    screenshot_thread.start()
    print("Screenshot recording thread started.")

    # Run the Flask development server.
    # It will be accessible at http://localhost:8082 by default.
    # use_reloader=False can be helpful to prevent the screenshot thread from starting twice in debug mode.
    print("Starting Flask development server on http://localhost:8082...")
    app.run(port=8082, debug=True, use_reloader=False)
