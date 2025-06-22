"""
Configuration module for OpenRecall.

This module handles the setup of application-specific configurations,
including command-line argument parsing for user-defined settings and
determination of appropriate application data storage paths based on
the operating system.
"""
import os
import sys
import argparse

# Initialize the argument parser with a description for the OpenRecall application.
parser = argparse.ArgumentParser(description="OpenRecall")

# Define command-line argument for specifying a custom storage path.
parser.add_argument(
    "--storage-path",
    default=None,  # Default is None, meaning the application will use a default OS-specific path.
    help="Path to store the screenshots and database",  # Help message displayed to the user.
)

# Define command-line argument for recording only the primary monitor.
parser.add_argument(
    "--primary-monitor-only",
    action="store_true",  # Stores True if the flag is present, False otherwise.
    help="Only record the primary monitor",  # Help message for the user.
    default=False,  # Default behavior is to record all monitors.
)

# Parse the command-line arguments provided when the script is run.
# The parsed arguments are stored in the 'args' object.
args = parser.parse_args()


def get_appdata_folder(app_name="openrecall"):
    """
    Determines the appropriate application data folder based on the operating system.

    This function supports Windows, macOS (darwin), and Linux platforms.
    It creates the folder if it doesn't already exist.

    Args:
        app_name (str, optional): The name of the application.
                                  Defaults to "openrecall".

    Returns:
        str: The absolute path to the application data folder.

    Raises:
        EnvironmentError: If the APPDATA environment variable is not set on Windows.
    """
    if sys.platform == "win32":  # Check if the operating system is Windows.
        appdata = os.getenv("APPDATA")  # Get the APPDATA environment variable.
        if not appdata:
            # Raise an error if APPDATA is not set, as it's crucial for determining the path.
            raise EnvironmentError("APPDATA environment variable is not set.")
        path = os.path.join(appdata, app_name)  # Construct path: %APPDATA%\app_name
    elif sys.platform == "darwin":  # Check if the operating system is macOS.
        home = os.path.expanduser("~")  # Get the user's home directory.
        # Construct path: ~/Library/Application Support/app_name
        path = os.path.join(home, "Library", "Application Support", app_name)
    else:  # Assume Linux or other Unix-like systems.
        home = os.path.expanduser("~")  # Get the user's home directory.
        # Construct path: ~/.local/share/app_name
        path = os.path.join(home, ".local", "share", app_name)

    # Create the directory if it does not exist.
    # os.makedirs will create parent directories as needed and won't raise an error if the directory already exists (due to exist_ok=True implicitly with how it's checked here).
    if not os.path.exists(path):
        os.makedirs(path)
    return path


# Determine the application data folder, database path, and screenshots path.
if args.storage_path:
    # If a custom storage path is provided via command-line argument, use it.
    appdata_folder = args.storage_path
    screenshots_path = os.path.join(appdata_folder, "screenshots")  # Path for storing screenshots.
    db_path = os.path.join(appdata_folder, "recall.db")  # Path for the SQLite database.
else:
    # If no custom path is provided, use the default OS-specific application data folder.
    appdata_folder = get_appdata_folder()
    db_path = os.path.join(appdata_folder, "recall.db")  # Path for the SQLite database.
    screenshots_path = os.path.join(appdata_folder, "screenshots")  # Path for storing screenshots.

# Ensure the screenshots directory exists.
if not os.path.exists(screenshots_path):
    try:
        # Create the screenshots directory.
        # os.makedirs will create parent directories if they don't exist.
        os.makedirs(screenshots_path)
    except Exception as e:
        # Pass silently if an error occurs (e.g., permission issues, or a race condition if another process creates it).
        # Ideally, specific exceptions should be caught and logged.
        # print(f"Could not create screenshots directory: {e}") # Example logging
        pass
