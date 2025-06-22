"""
Utility functions for OpenRecall.

This module provides a collection of helper functions for various purposes,
including:
- Time conversions (Unix timestamp to human-readable formats).
- Platform-specific operations to get active application name and window title
  for macOS, Windows, and Linux.
- Platform-specific checks for user activity status.

It uses conditional imports to handle missing platform-specific libraries gracefully,
allowing the application to run with reduced functionality on systems where these
dependencies are not met. For Linux, it relies on external command-line utilities
like `xprop` and `xprintidle`.
"""
import sys
import datetime
import re
import subprocess # subprocess is generally available, moved out of try-except for clarity

# ORIGINAL COMMENT: Platform-specific imports with error handling

# Attempt to import Windows-specific libraries
try:
    import psutil
    import win32gui
    import win32process
    import win32api
except ImportError:
    # If any of these imports fail (e.g., not on Windows or pywin32/psutil not installed),
    # set them to None so functions can check their availability.
    psutil = None
    win32gui = None
    win32process = None
    win32api = None
    # print("Windows specific libraries (psutil, pywin32) not found. Windows functionality will be limited.") # Optional: logging/warning

# Attempt to import macOS-specific libraries (pyobjc)
try:
    from AppKit import NSWorkspace
except ImportError:
    NSWorkspace = None
    # print("macOS specific library (AppKit) not found. macOS functionality will be limited.") # Optional: logging/warning

try:
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGNullWindowID,
        kCGWindowListOptionOnScreenOnly,
    )
except ImportError:
    CGWindowListCopyWindowInfo = None
    kCGNullWindowID = None
    kCGWindowListOptionOnScreenOnly = None
    # print("macOS specific library (Quartz) not found. macOS functionality will be limited.") # Optional: logging/warning

# subprocess itself should usually be available as it's part of the standard library.
# The original code had a try-except for it, which is usually not necessary.
# If it *were* missing, many things would break. Kept for consistency if there was a specific reason.
# ORIGINAL COMMENT: subprocess = None  # Should always be available in standard lib


def human_readable_time(timestamp: int) -> str:
    # ORIGINAL COMMENT: """Converts a Unix timestamp into a human-readable relative time string.
    """
    Converts a Unix timestamp into a human-readable relative time string
    (e.g., "5 minutes ago", "2 hours ago", "3 days ago").

    Args:
        timestamp (int): The Unix timestamp (seconds since the epoch).

    Returns:
        str: A string representing the relative time difference from now.
    # ORIGINAL COMMENT: """
    now = datetime.datetime.now()
    dt_object = datetime.datetime.fromtimestamp(timestamp)
    diff = now - dt_object

    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds < 60: # Less than a minute
        return f"{diff.seconds} seconds ago"
    elif diff.seconds < 3600: # Less than an hour
        return f"{diff.seconds // 60} minutes ago"
    else: # Hours
        return f"{diff.seconds // 3600} hours ago"


def timestamp_to_human_readable(timestamp: int) -> str:
    # ORIGINAL COMMENT: """Converts a Unix timestamp into a human-readable absolute date/time string.
    """
    Converts a Unix timestamp into a human-readable absolute date and time string
    in the format "YYYY-MM-DD HH:MM:SS".

    Args:
        timestamp (int): The Unix timestamp (seconds since the epoch).

    Returns:
        str: A string representing the absolute date and time (e.g., "2023-03-15 10:30:00"),
             or an empty string if the timestamp is invalid or conversion fails.
    # ORIGINAL COMMENT: """
    try:
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        # Ensure format string is correct for strftime: %Y-%m-%d
        return dt_object.strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError) as e: # Catch potential errors from invalid timestamps
        print(f"Error converting timestamp '{timestamp}' to human-readable format: {e}")
        return ""


def get_active_app_name_osx() -> str:
    # ORIGINAL COMMENT: """Gets the name of the active application on macOS.
    """
    Gets the name of the currently active application on macOS.

    This function relies on the `pyobjc` package, specifically the `AppKit.NSWorkspace`
    class. If `pyobjc` is not installed or `NSWorkspace` cannot be imported,
    it returns an empty string.

    Returns:
        str: The name of the active application (e.g., "Finder", "Google Chrome").
             Returns an empty string if the information is unavailable or an error occurs.
    # ORIGINAL COMMENT: """
    if NSWorkspace is None:
        # ORIGINAL COMMENT: return ""  # Indicate unavailability if import failed
        # This check ensures that if AppKit didn't import, we don't try to use NSWorkspace.
        return ""
    try:
        # Get the shared workspace instance.
        shared_workspace = NSWorkspace.sharedWorkspace()
        # Get information about the active application.
        active_app_info = shared_workspace.activeApplication()
        # Extract the application name from the dictionary.
        # "NSApplicationName" is the key for the application's localized name.
        return active_app_info.get("NSApplicationName", "") # Default to "" if key missing
    except Exception as e:
        # Catch any other unexpected errors during the pyobjc call.
        print(f"Error getting active app name on macOS: {e}")
        return ""


def get_active_window_title_osx() -> str:
    # ORIGINAL COMMENT: """Gets the title of the active window on macOS.
    """
    Gets the title of the currently active (frontmost) window on macOS.

    This function uses `pyobjc` (specifically `AppKit` for the active app name
    and `Quartz` for window information) to find the window associated with the
    active application that is currently in the foreground.

    It iterates through the list of on-screen windows, looking for one that
    belongs to the active application, is on the normal window layer (0),
    and has a title.

    Returns:
        str: The title of the active window. Returns an empty string if unavailable,
             no suitable window is found, or an error occurs.
    # ORIGINAL COMMENT: """
    if CGWindowListCopyWindowInfo is None or kCGNullWindowID is None or kCGWindowListOptionOnScreenOnly is None or NSWorkspace is None:
        # ORIGINAL COMMENT: return ""  # Indicate unavailability if import failed
        # If any required Quartz or AppKit components are missing, cannot proceed.
        return ""
    try:
        app_name = get_active_app_name_osx()
        if not app_name:
            # If we can't get the active app name, we can't reliably find its window title.
            return ""

        # ORIGINAL COMMENT: Get window list ordered front-to-back
        # These options specify to get only on-screen windows.
        options = kCGWindowListOptionOnScreenOnly
        # Copy the list of window information dictionaries.
        window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

        if window_list is None: # Ensure window_list is not None before iterating
            return ""

        for window_info_dict in window_list:
            # ORIGINAL COMMENT: Check if the window belongs to the active application
            owner_name = window_info_dict.get("kCGWindowOwnerName")
            if owner_name == app_name:
                # ORIGINAL COMMENT: Check if it's a normal window (layer 0) and has a title
                # kCGWindowLayer == 0 usually indicates a standard application window.
                if window_info_dict.get("kCGWindowLayer") == 0 and "kCGWindowName" in window_info_dict:
                    title = window_info_dict.get("kCGWindowName", "")
                    # ORIGINAL COMMENT: if title:  # Return the first non-empty title found
                    if title:  # Ensure the title is not an empty string.
                        return title
        # ORIGINAL COMMENT: Fallback if no suitable window title found for the active app
        return ""
    except Exception as e:
        print(f"Error getting macOS window title: {e}")
        return ""
    # ORIGINAL COMMENT: return ""  # Default if no specific window is found
    # This line is technically unreachable due to the try-except returning earlier or the final return in try.
    # However, it's harmless.


def get_active_app_name_windows() -> str:
    # ORIGINAL COMMENT: """Gets the name of the executable for the active window on Windows.
    """
    Gets the name of the executable file for the process owning the foreground window on Windows.

    Requires `pywin32` (for window and process information) and `psutil` (to get
    the process name from its ID).

    Returns:
        str: The executable name (e.g., "chrome.exe", "explorer.exe").
             Returns an empty string if unavailable, dependencies are missing, or an error occurs.
    # ORIGINAL COMMENT: """
    if not all([psutil, win32gui, win32process]): # Check if all required modules were imported.
        # ORIGINAL COMMENT: return ""  # Indicate unavailability if imports failed
        return ""
    try:
        hwnd = win32gui.GetForegroundWindow() # Get handle to the foreground window.
        if not hwnd: # No foreground window found.
            return ""
        # Get the process ID (PID) of the thread that created the window.
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid: # Could not get PID.
            return ""
        process = psutil.Process(pid) # Get a psutil Process object for the PID.
        exe_name = process.name() # Get the executable name of the process.
        return exe_name
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
        # Catch specific errors from psutil or general exceptions.
        # print(f"Error getting Windows app name: {e}") # Optional: for debugging
        return ""


def get_active_window_title_windows() -> str:
    # ORIGINAL COMMENT: """Gets the title of the active window on Windows.
    """
    Gets the title of the currently active (foreground) window on Windows.

    Requires the `pywin32` package (specifically `win32gui`).

    Returns:
        str: The title text of the foreground window.
             Returns an empty string if unavailable, no foreground window,
             dependencies are missing, or an error occurs.
    # ORIGINAL COMMENT: """
    if win32gui is None: # Check if win32gui was imported.
        # ORIGINAL COMMENT: return ""  # Indicate unavailability if import failed
        return ""
    try:
        hwnd = win32gui.GetForegroundWindow() # Get handle to the foreground window.
        if not hwnd: # No foreground window.
            return ""
        return win32gui.GetWindowText(hwnd) # Get the window's title text.
    except Exception as e:
        # Catch any errors during the win32gui call.
        print(f"Error getting Windows window title: {e}")
        return ""


def get_active_app_name_linux() -> str:
    # ORIGINAL COMMENT: """Gets the name of the active application on Linux.
    # ORIGINAL COMMENT: Placeholder implementation. Requires additional logic (e.g., using xprop
    # ORIGINAL COMMENT: or similar tools/libraries).
    """
    Gets the instance name of the active window's class on Linux using `xprop`.

    This function relies on the `xprop` command-line utility being available.
    It first determines the ID of the active window, then queries its `WM_CLASS`
    property. The `WM_CLASS` property typically contains two strings: instance name
    and class name. This function returns the instance name.

    Returns:
        str: The instance name of the active window's class (e.g., "google-chrome", "gnome-terminal").
             Returns an empty string if `xprop` is unavailable, fails, or the
             property cannot be parsed.
    # ORIGINAL COMMENT: """
    if subprocess is None: # Should not happen with standard Python.
        print("Warning: 'subprocess' module not available for Linux app name check.")
        return ""
    try:
        # ORIGINAL COMMENT: Get active window ID
        # Command to get the ID of the _NET_ACTIVE_WINDOW (current active window).
        active_window_cmd = ['xprop', '-root', '_NET_ACTIVE_WINDOW']
        # Execute the command.
        active_window_proc = subprocess.Popen(active_window_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Communicate with the process, get output, handle timeout.
        stdout, stderr = active_window_proc.communicate(timeout=1) # 1-second timeout.
        if active_window_proc.returncode != 0:
            # print(f"Error running xprop for active window: {stderr.decode(errors='replace')}") # Optional: for debugging
            return ""

        # Parse the output to find the window ID (e.g., "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x1234567")
        match = re.search(rb'window id # (0x[0-9a-fA-F]+)', stdout)
        if not match:
            # print("Could not find active window ID using xprop.") # Optional: for debugging
            return ""
        window_id = match.group(1).decode('utf-8') # Extract the hex window ID.

        # ORIGINAL COMMENT: Get WM_CLASS for the window ID
        # Command to get the WM_CLASS property for the identified window.
        wm_class_cmd = ['xprop', '-id', window_id, 'WM_CLASS']
        wm_class_proc = subprocess.Popen(wm_class_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = wm_class_proc.communicate(timeout=1)
        if wm_class_proc.returncode != 0:
            # print(f"Error running xprop for WM_CLASS: {stderr.decode(errors='replace')}") # Optional: for debugging
            return ""

        # ORIGINAL COMMENT: WM_CLASS(STRING) = "instance", "class"
        # Parse WM_CLASS output (e.g., WM_CLASS(STRING) = "Navigator", "Firefox")
        match = re.search(rb'WM_CLASS\(STRING\) = "([^"]+)"(?:, "([^"]+)")?', stdout)
        if match:
            # ORIGINAL COMMENT: Return the instance name if available, otherwise the class name
            instance_name = match.group(1).decode('utf-8', errors='replace')
            # class_name = match.group(2).decode('utf-8', errors='replace') if match.group(2) else None # Class name also available
            return instance_name
        else:
            # print(f"Could not parse WM_CLASS for window ID {window_id}.") # Optional: for debugging
            return ""

    except FileNotFoundError:
        print("Error: 'xprop' command not found. Please ensure 'xprop' (usually part of x11-utils) is installed and in PATH.")
        return ""
    except subprocess.TimeoutExpired:
        print("Error: 'xprop' command timed out while getting app name.")
        return ""
    except Exception as e:
         print(f"An unexpected error occurred while getting Linux app name: {e}")
         return ""


def get_active_window_title_linux() -> str:
    # ORIGINAL COMMENT: """Gets the title of the active window on Linux.
    # ORIGINAL COMMENT: Placeholder implementation. Requires additional logic (e.g., using xprop
    # ORIGINAL COMMENT: or similar tools/libraries).
    """
    Gets the title of the active window on Linux using `xprop`.

    This function relies on the `xprop` command-line utility. It first finds the
    active window ID, then attempts to get its title by checking the `_NET_WM_NAME`
    (preferred, UTF-8) and `WM_NAME` (legacy) properties.

    Returns:
        str: The title of the active window. Returns an empty string if `xprop` is
             unavailable, fails, or the title cannot be found/parsed.
    # ORIGINAL COMMENT: """
    if subprocess is None:
        print("Warning: 'subprocess' module not available for Linux window title check.")
        return ""
    try:
        # ORIGINAL COMMENT: Get active window ID
        active_window_cmd = ['xprop', '-root', '_NET_ACTIVE_WINDOW']
        active_window_proc = subprocess.Popen(active_window_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = active_window_proc.communicate(timeout=1)
        if active_window_proc.returncode != 0:
            # print(f"Error running xprop for active window (title check): {stderr.decode(errors='replace')}") # Optional
            return ""

        match = re.search(rb'window id # (0x[0-9a-fA-F]+)', stdout)
        if not match:
            # print("Could not find active window ID using xprop (title check).") # Optional
            return ""
        window_id = match.group(1).decode('utf-8')

        # ORIGINAL COMMENT: Get _NET_WM_NAME (UTF-8 title) or WM_NAME (legacy title)
        # Try common properties for window title. _NET_WM_NAME is preferred as it's UTF-8.
        for prop_name in ['_NET_WM_NAME', 'WM_NAME']:
            title_cmd = ['xprop', '-id', window_id, prop_name]
            title_proc = subprocess.Popen(title_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = title_proc.communicate(timeout=1) # 1-second timeout.

            if title_proc.returncode == 0: # If command succeeded for this property
                title_match = None
                if prop_name == '_NET_WM_NAME':
                    # ORIGINAL COMMENT: _NET_WM_NAME(UTF8_STRING) = "Title"
                    title_match = re.search(rb'_NET_WM_NAME\(UTF8_STRING\) = "([^"]*)"', stdout)
                else: # WM_NAME
                    # ORIGINAL COMMENT: WM_NAME(STRING) = "Title"
                    title_match = re.search(rb'WM_NAME\([^)]*\) = "([^"]*)"', stdout) # More general WM_NAME format

                if title_match:
                    # ORIGINAL COMMENT: title = match.group(1).decode('utf-8', errors='replace') # Decode UTF-8, replace errors
                    title = title_match.group(1).decode('utf-8', errors='replace')
                    return title # Return the first successfully found and decoded title.

        # ORIGINAL COMMENT: If neither property provided a title
        # print(f"Could not find window title for window ID {window_id} using _NET_WM_NAME or WM_NAME.") # Optional
        return ""

    except FileNotFoundError:
        print("Error: 'xprop' command not found. Please ensure 'xprop' (usually part of x11-utils) is installed and in PATH.")
        return ""
    except subprocess.TimeoutExpired:
        print("Error: 'xprop' command timed out while getting window title.")
        return ""
    except Exception as e:
        print(f"An unexpected error occurred while getting Linux window title: {e}")
        return ""

def get_active_app_name() -> str:
    # ORIGINAL COMMENT: """Gets the active application name for the current platform.
    """
    Gets the active application name based on the current operating system.

    This function acts as a dispatcher, calling the appropriate platform-specific
    implementation (`get_active_app_name_windows`, `get_active_app_name_osx`,
    `get_active_app_name_linux`).

    Returns:
        str: The name of the active application. Returns an empty string if
             the information is unavailable on the current platform or if an
             error occurs in the platform-specific function.

    Raises:
        NotImplementedError: If the current platform (`sys.platform`) is not
                             Windows, macOS (darwin), or Linux.
    # ORIGINAL COMMENT: """
    if sys.platform == "win32":
        return get_active_app_name_windows()
    elif sys.platform == "darwin": # macOS
        return get_active_app_name_osx()
    elif sys.platform.startswith("linux"): # Covers "linux", "linux2", etc.
        return get_active_app_name_linux()
    else:
        # Raise an error for unsupported platforms to make it clear.
        raise NotImplementedError(f"Platform '{sys.platform}' not supported yet for get_active_app_name")


def get_active_window_title() -> str:
    # ORIGINAL COMMENT: """Gets the active window title for the current platform.
    """
    Gets the active window title based on the current operating system.

    This function dispatches to platform-specific implementations like
    `get_active_window_title_windows`, `get_active_window_title_osx`,
    or `get_active_window_title_linux`.

    Returns:
        str: The title of the active window. Returns an empty string if the
             information is unavailable or an error occurs in the platform-specific
             function.

    Raises:
        NotImplementedError: If the current platform (`sys.platform`) is not
                             Windows, macOS (darwin), or Linux.
    # ORIGINAL COMMENT: """
    if sys.platform == "win32":
        return get_active_window_title_windows()
    elif sys.platform == "darwin":
        return get_active_window_title_osx()
    elif sys.platform.startswith("linux"):
        return get_active_window_title_linux()
    else:
        # Provide a warning and raise error for unsupported platforms.
        print(f"Warning: Active window title retrieval not implemented for platform '{sys.platform}'.")
        raise NotImplementedError(f"Platform '{sys.platform}' not supported yet for get_active_window_title")


def is_user_active_osx() -> bool:
    # ORIGINAL COMMENT: """Checks if the user is active on macOS based on HID idle time.
    # ORIGINAL COMMENT: Requires the pyobjc package and uses the 'ioreg' command. Considers the user
    # ORIGINAL COMMENT: active if the idle time is less than 5 seconds.
    # ORIGINAL COMMENT: Returns:
    # ORIGINAL COMMENT:     True if the user is considered active, False otherwise. Returns True
    # ORIGINAL COMMENT:     if the check fails for any reason.
    # ORIGINAL COMMENT: """
    """
    Checks if the user is active on macOS by querying the HID system idle time.

    Uses the `ioreg` command-line utility to get the `HIDIdleTime` property,
    which represents the time since the last HID (Human Interface Device, e.g.,
    mouse or keyboard) event in nanoseconds.

    The user is considered active if this idle time is less than 5 seconds.

    Returns:
        bool: True if the user is considered active (idle < 5 seconds).
              Returns True (assumes active) as a fallback if `ioreg` fails,
              times out, `subprocess` module is unavailable, or output parsing fails.
    """
    if subprocess is None:
        print("Warning: 'subprocess' module not available for macOS idle check, assuming user is active.")
        return True # Fallback if subprocess is somehow missing.
    try:
        # ORIGINAL COMMENT: Run the 'ioreg' command to get idle time information
        # ORIGINAL COMMENT: Filtering directly with -k is more efficient
        # Command to query IOHIDSystem for the HIDIdleTime.
        cmd = ["ioreg", "-c", "IOHIDSystem", "-r", "-k", "HIDIdleTime"]
        # Execute the command, capture output, with a timeout.
        output = subprocess.check_output(cmd, timeout=1).decode('utf-8', errors='replace')

        # ORIGINAL COMMENT: Find the line containing "HIDIdleTime"
        for line in output.splitlines():
            if "HIDIdleTime" in line:
                # ORIGINAL COMMENT: Extract the idle time value
                # Example line: | |   |   "HIDIdleTime" = 123456789
                idle_time_ns_str = line.split("=")[-1].strip()
                idle_time_ns = int(idle_time_ns_str)

                # ORIGINAL COMMENT: Convert idle time from nanoseconds to seconds
                idle_seconds = idle_time_ns / 1_000_000_000  # ORIGINAL COMMENT: Use underscore for clarity

                # ORIGINAL COMMENT: If idle time is less than 5 seconds, consider the user active
                return idle_seconds < 5.0 # Threshold for activity.

        # ORIGINAL COMMENT: If "HIDIdleTime" is not found (e.g., screen locked), assume inactive?
        # ORIGINAL COMMENT: Or assume active as a fallback? Let's assume active for now.
        # If parsing fails or HIDIdleTime not found, log and assume active.
        print("Warning: Could not find HIDIdleTime in ioreg output for macOS. Assuming user is active.")
        return True

    except subprocess.TimeoutExpired:
        print("Warning: 'ioreg' command timed out during macOS idle check. Assuming user is active.")
        return True
    except subprocess.CalledProcessError as e:
        # ORIGINAL COMMENT: This might happen if the class IOHIDSystem is not found, etc.
        print(f"Warning: 'ioreg' command failed for macOS idle check (Error: {e}). Assuming user is active.")
        return True
    except ValueError as e: # Handles int() conversion error
        print(f"Warning: Could not parse HIDIdleTime from ioreg output for macOS (Error: {e}). Assuming user is active.")
        return True
    except Exception as e:
        # ORIGINAL COMMENT: Fallback: assume the user is active
        print(f"An unexpected error occurred during macOS idle check: {e}. Assuming user is active.")
        return True


def is_user_active_windows() -> bool:
    # ORIGINAL COMMENT: """Checks if the user is active on Windows based on last input time.
    # ORIGINAL COMMENT: Requires the pywin32 package. Considers the user active if the last input
    # ORIGINAL COMMENT: was less than 5 seconds ago.
    # ORIGINAL COMMENT: Returns:
    # ORIGINAL COMMENT:     True if the user is considered active, False otherwise. Returns True
    # ORIGINAL COMMENT:     if the check fails.
    # ORIGINAL COMMENT: """
    """
    Checks if the user is active on Windows by comparing the time of the last
    user input event with the current time.

    Uses `win32api.GetLastInputInfo()` to get the tick count of the last input event
    and `win32api.GetTickCount()` for the current system tick count. The user is
    considered active if the difference is less than 5 seconds.

    Requires the `pywin32` package.

    Returns:
        bool: True if the user is considered active (idle < 5 seconds).
              Returns True (assumes active) as a fallback if `win32api` is
              unavailable or the API call fails.
    """
    if win32api is None: # Check if pywin32 was imported.
        print("Warning: 'win32api' module not available for Windows idle check. Assuming user is active.")
        return True
    try:
        # GetTickCount returns milliseconds since the system was started.
        # GetLastInputInfo returns the tick count of the last input event.
        last_input_tick = win32api.GetLastInputInfo()
        # ORIGINAL COMMENT: current_time = win32api.GetTickCount()
        current_tick = win32api.GetTickCount()

        # Calculate idle time in milliseconds. Handle potential tick count wraparound (though rare for short intervals).
        # If current_tick is less than last_input_tick, it means GetTickCount has wrapped around.
        # For typical uptimes and short idle checks, this is unlikely to be an issue.
        # A more robust solution might involve GetTickCount64 if available/necessary.
        if current_tick < last_input_tick: # Tick count wrapped around
             # This logic is simplified; a full solution for wraparound is more complex.
             # For a 5-second idle check, simple subtraction is usually fine.
             idle_milliseconds = (0xFFFFFFFF - last_input_tick) + current_tick
        else:
             idle_milliseconds = current_tick - last_input_tick

        idle_seconds = idle_milliseconds / 1000.0
        return idle_seconds < 5.0 # User active if idle less than 5 seconds.
    except Exception as e:
        # ORIGINAL COMMENT: Fallback: assume the user is active
        print(f"An error occurred during Windows idle check: {e}. Assuming user is active.")
        return True


def is_user_active_linux() -> bool:
    # ORIGINAL COMMENT: """Checks if the user is active on Linux.
    # ORIGINAL COMMENT: Placeholder implementation. Requires interaction with the display server
    # ORIGINAL COMMENT: (X11 or Wayland) to get idle time. Uses 'xprintidle'.
    # ORIGINAL COMMENT: Returns:
    # ORIGINAL COMMENT:     True if the user is considered active (idle < 5s), False otherwise.
    # ORIGINAL COMMENT:     Returns True if the check fails or 'xprintidle' is not available.
    # ORIGINAL COMMENT: """
    """
    Checks if the user is active on Linux using the `xprintidle` command-line utility.

    `xprintidle` reports the user's idle time in milliseconds for an X11 session.
    The user is considered active if this idle time is less than 5 seconds.

    Returns:
        bool: True if the user is considered active (idle < 5 seconds).
              Returns True (assumes active) as a fallback if `xprintidle` is not found,
              fails, times out, or its output cannot be parsed.
    """
    if subprocess is None:
        # ORIGINAL COMMENT: print("Warning: 'subprocess' module not available for Linux idle check.")
        # ORIGINAL COMMENT: return True # Assume active if module missing
        # This case is highly unlikely for standard Python installations.
        return True
    try:
        # ORIGINAL COMMENT: Run xprintidle to get idle time in milliseconds
        # Execute `xprintidle`, capture its output.
        cmd = ['xprintidle']
        output = subprocess.check_output(cmd, timeout=1).decode('utf-8', errors='replace')
        idle_milliseconds = int(output.strip()) # Convert output (string of ms) to integer.
        idle_seconds = idle_milliseconds / 1000.0
        return idle_seconds < 5.0 # Active if idle less than 5 seconds.
    except FileNotFoundError:
        # ORIGINAL COMMENT: print("Warning: 'xprintidle' command not found. Please install xprintidle to check user activity.")
        # ORIGINAL COMMENT: return True # Assume active if command missing
        # xprintidle might not be installed.
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        # ORIGINAL COMMENT: print(f"Warning: Could not check Linux idle time ({e}), assuming user is active.")
        # Command failed or timed out.
        return True
    except ValueError as e: # Handles int() conversion error if output is not a number.
        # ORIGINAL COMMENT: print(f"Warning: Could not parse output of xprintidle ('{output.strip()}'): {e}, assuming user is active.")
        return True
    except Exception as e:
        # ORIGINAL COMMENT: print(f"An error occurred during Linux idle check: {e}")
        # ORIGINAL COMMENT: return True # Assume active on other errors
        # Catch any other unexpected errors.
        return True


def is_user_active() -> bool:
    # ORIGINAL COMMENT: """Checks if the user is active on the current platform.
    # ORIGINAL COMMENT: Considers the user active if their last input was recent (e.g., < 5 seconds ago).
    # ORIGINAL COMMENT: Implementation varies by platform.
    # ORIGINAL COMMENT: Returns:
    # ORIGINAL COMMENT:     True if the user is considered active, False otherwise. Returns True
    # ORIGINAL COMMENT:     if the check is not implemented or fails.
    # ORIGINAL COMMENT: """
    """
    Checks if the user is currently active on the system, based on recent input.

    This function dispatches to platform-specific implementations. It generally
    considers the user active if their last input (keyboard/mouse) was within
    the last 5 seconds.

    Returns:
        bool: True if the user is determined to be active or if the check fails
              (as a safe default). False if determined to be inactive.

    Raises:
        NotImplementedError: If the current platform (`sys.platform`) is not
                             Windows, macOS (darwin), or Linux.
    """
    if sys.platform == "win32":
        return is_user_active_windows()
    elif sys.platform == "darwin": # macOS
        return is_user_active_osx()
    elif sys.platform.startswith("linux"): # Linux
        return is_user_active_linux()
    else:
        # ORIGINAL COMMENT: print(f"Warning: User active check not supported for platform '{sys.platform}', assuming active.")
        # For unknown platforms, it's better to raise an error than assume active,
        # as "assuming active" might lead to incorrect application behavior.
        raise NotImplementedError(f"Platform '{sys.platform}' not supported yet for is_user_active")
