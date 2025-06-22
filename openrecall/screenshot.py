"""
Screenshot capture, processing, and storage module for OpenRecall.

This module is responsible for the core functionality of periodically capturing
screenshots, determining if they are significantly different from previous
captures, and if so, processing them through OCR and NLP, then storing
the results (image, text, embedding, metadata) in the database.

It includes utilities for image similarity comparison (MSSIM), multi-monitor
screenshot capture, and the main recording loop designed to run in a thread.

Note: This file contains two definitions of `record_screenshots_thread`.
As per user instruction, both will be commented, but the first, more complex
one appears to be the primary intended version.
"""
import os
import time
from typing import List, Tuple, Optional # Added Optional for clarity

import mss # For screen capture
import numpy as np
from PIL import Image # For image manipulation and saving

# Application-specific imports
from openrecall.config import screenshots_path, args # For storage paths and runtime arguments
from openrecall.database import insert_entry # For saving data to the database
from openrecall.nlp import get_embedding # For generating text embeddings
from openrecall.ocr import extract_text_from_image # For extracting text from images
from openrecall.utils import (
    get_active_app_name,
    get_active_window_title,
    is_user_active,
)


def mean_structured_similarity_index(
    img1: np.ndarray, img2: np.ndarray, L: int = 255
) -> float:
    # ORIGINAL COMMENT: """Calculates the Mean Structural Similarity Index (MSSIM) between two images.
    """
    Calculates the Mean Structural Similarity Index (MSSIM) between two images.

    MSSIM is a method for predicting the perceived quality of digital images
    and videos. It measures similarity based on luminance, contrast, and structure.

    Args:
        img1 (np.ndarray): The first image as a NumPy array (H, W, C) in RGB format.
        img2 (np.ndarray): The second image as a NumPy array (H, W, C) in RGB format.
        L (int, optional): The dynamic range of the pixel values. Defaults to 255
                           (for 8-bit grayscale images).

    Returns:
        float: The MSSIM value between the two images. Ranges from -1 to 1, where
               1 indicates perfect similarity.
    # ORIGINAL COMMENT: """
    # Constants for MSSIM calculation, as defined in the original paper by Wang et al.
    K1, K2 = 0.01, 0.03
    C1, C2 = (K1 * L) ** 2, (K2 * L) ** 2 # Constants to stabilize division with weak denominator

    def rgb2gray(img: np.ndarray) -> np.ndarray:
        # ORIGINAL COMMENT: """Converts an RGB image to grayscale."""
        """
        Converts an RGB image (NumPy array) to grayscale using standard luminosity coefficients.
        Args:
            img (np.ndarray): Input RGB image array.
        Returns:
            np.ndarray: Grayscale image array.
        """
        # Standard NTSC conversion formula for RGB to Grayscale
        return 0.2989 * img[..., 0] + 0.5870 * img[..., 1] + 0.1140 * img[..., 2]

    # Convert images to grayscale as MSSIM is typically calculated on single-channel images.
    img1_gray: np.ndarray = rgb2gray(img1)
    img2_gray: np.ndarray = rgb2gray(img2)

    # Calculate means
    mu1: float = np.mean(img1_gray)
    mu2: float = np.mean(img2_gray)

    # Calculate variances
    sigma1_sq = np.var(img1_gray)
    sigma2_sq = np.var(img2_gray)

    # Calculate covariance
    sigma12 = np.mean((img1_gray - mu1) * (img2_gray - mu2))

    # MSSIM formula components
    numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
    denominator = (mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2)

    ssim_index = numerator / denominator
    return ssim_index


def is_similar(
    img1: np.ndarray, img2: np.ndarray, similarity_threshold: float = 0.9
) -> bool:
    # ORIGINAL COMMENT: """Checks if two images are similar based on MSSIM.
    """
    Checks if two images are similar based on their Mean Structural Similarity Index (MSSIM).

    Args:
        img1 (np.ndarray): The first image as a NumPy array.
        img2 (np.ndarray): The second image as a NumPy array.
        similarity_threshold (float, optional): The threshold (between -1 and 1)
                                               above which images are considered similar.
                                               Defaults to 0.9.

    Returns:
        bool: True if the MSSIM value is greater than or equal to the similarity_threshold,
              False otherwise.
    # ORIGINAL COMMENT: """
    similarity: float = mean_structured_similarity_index(img1, img2)
    return similarity >= similarity_threshold


def take_screenshots() -> List[np.ndarray]:
    # ORIGINAL COMMENT: """Takes screenshots of all connected monitors or just the primary one.
    """
    Takes screenshots of all connected monitors or only the primary one,
    based on the `args.primary_monitor_only` command-line argument.

    Uses the `mss` library for screen capture. `mss.monitors` provides a list
    where index 0 is a composite of all monitors, index 1 is the primary,
    and subsequent indices are other monitors.

    Returns:
        List[np.ndarray]: A list of screenshots. Each screenshot is a NumPy array
                          representing an RGB image (height, width, 3 channels).
                          Returns an empty list if no monitors are captured.
    # ORIGINAL COMMENT: """
    screenshots: List[np.ndarray] = []
    with mss.mss() as sct: # Initialize mss context manager for screen capture
        # ORIGINAL COMMENT: sct.monitors[0] is the combined view of all monitors
        # ORIGINAL COMMENT: sct.monitors[1] is the primary monitor
        # ORIGINAL COMMENT: sct.monitors[2:] are other monitors

        # By default, capture all individual monitors, skipping the composite view at index 0.
        monitor_indices = range(1, len(sct.monitors))

        if args.primary_monitor_only:
            # If only primary monitor is requested, target index 1.
            # Ensure there's at least one monitor beyond the composite view.
            monitor_indices = [1] if len(sct.monitors) > 1 else []


        for i in monitor_indices:
            # ORIGINAL COMMENT: Ensure the index is valid before attempting to grab
            if i < len(sct.monitors):
                monitor_info = sct.monitors[i] # Get monitor dimensions and offset
                # ORIGINAL COMMENT: Grab the screen
                sct_img = sct.grab(monitor_info) # Capture the screen region for this monitor

                # ORIGINAL COMMENT: Convert to numpy array and change BGRA to RGB
                # mss captures in BGRA format by default. Convert to NumPy array and then to RGB.
                img_bgra = np.array(sct_img)
                # Slicing to reorder color channels: B (0), G (1), R (2), A (3)
                # We select [:, :, :3] to take only BGR, then [..., ::-1] to reverse to RGB, or select channels directly.
                screenshot_rgb = img_bgra[:, :, [2, 1, 0]] # Selects R, G, B channels from BGRA
                screenshots.append(screenshot_rgb)
            else:
                # ORIGINAL COMMENT: Handle case where primary_monitor_only is True but only one monitor exists (all monitors view)
                # ORIGINAL COMMENT: This case might need specific handling depending on desired behavior.
                # ORIGINAL COMMENT: For now, we just skip if the index is out of bounds.
                # This warning helps diagnose issues if monitor indices are unexpected.
                print(f"Warning: Monitor index {i} out of bounds. Total monitors (including composite): {len(sct.monitors)}. Skipping.")
    return screenshots


# This appears to be the primary, more detailed version of the recording thread.
def record_screenshots_thread() -> None: # Return type hint was None, but function has an unreachable return.
    # ORIGINAL COMMENT: """
    # ORIGINAL COMMENT: Continuously records screenshots, processes them, and stores relevant data.
    #
    # ORIGINAL COMMENT: Checks for user activity and image similarity before processing and saving
    # ORIGINAL COMMENT: screenshots, associated OCR text, embeddings, and active application info.
    # ORIGINAL COMMENT: Runs in an infinite loop, intended to be executed in a separate thread.
    # ORIGINAL COMMENT: """
    """
    Continuously records screenshots from all specified monitors, processes them if
    they are new and the user is active, and stores relevant data (image, OCR text,
    text embedding, active application name, window title, and filename) into the database.

    This function is designed to run in an infinite loop and is typically executed
    in a separate thread to avoid blocking the main application.

    Workflow:
    1. Initializes by taking an initial set of screenshots.
    2. Enters an infinite loop:
        a. Checks if the user is active. If not, sleeps for a longer duration.
        b. Takes new screenshots.
        c. If monitor configuration changed, resets baseline and continues.
        d. For each monitor's screenshot:
            i. Compares with the last known screenshot for that monitor using MSSIM.
            ii. If significantly different:
                - Updates the last known screenshot for that monitor.
                - Saves the new screenshot as a lossless WebP image.
                - Extracts text using OCR.
                - If text is found:
                    - Generates a semantic embedding for the text.
                    - Retrieves active application name and window title.
                    - Inserts all data into the database.
        e. Sleeps for a short duration before the next cycle.

    Note: This function contains an environment variable setting for `TOKENIZERS_PARALLELISM`
    and an unreachable `return screenshots` statement at the end of the loop.
    """
    # ORIGINAL COMMENT: TODO: Move this environment variable setting to the application's entry point.
    # ORIGINAL COMMENT: HACK: Prevents a warning/error from the huggingface/tokenizers library
    # ORIGINAL COMMENT: when used in environments where multiprocessing fork safety is a concern.
    # This environment variable is set to 'false' to potentially avoid issues with
    # parallelism in the 'tokenizers' library, often used by 'sentence-transformers'.
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # Capture initial screenshots to have a baseline for comparison.
    last_screenshots: List[np.ndarray] = take_screenshots()

    while True: # Main recording loop.
        if not is_user_active():
            time.sleep(3)  # ORIGINAL COMMENT: Wait longer if user is inactive
            continue # Skip the rest of the loop if user is not active.

        current_screenshots: List[np.ndarray] = take_screenshots()

        # ORIGINAL COMMENT: Ensure we have a last_screenshot for each current_screenshot
        # ORIGINAL COMMENT: This handles cases where monitor setup might change (though unlikely mid-run)
        if len(last_screenshots) != len(current_screenshots):
             # ORIGINAL COMMENT: If monitor count changes, reset last_screenshots and continue
             # This simplistic handling assumes the order of monitors in list might correspond.
             # A more robust solution might involve tracking monitors by ID if available.
             last_screenshots = current_screenshots
             time.sleep(3) # Wait a bit before next cycle after reset.
             continue

        # Process each monitor's screenshot.
        for i, current_screenshot in enumerate(current_screenshots):
            # Ensure we have a corresponding last_screenshot for comparison.
            # This check is somewhat redundant due to the len check above but provides safety.
            if i >= len(last_screenshots):
                # This case should ideally not be hit if len check is effective.
                # Consider adding the new screen to last_screenshots or logging.
                # For now, if it happens, we might just update last_screenshots for this new index.
                if i < len(current_screenshots): # Check if current_screenshot is valid
                    last_screenshots.append(current_screenshot[i]) # Append if extending, or handle differently
                continue


            last_screenshot_for_monitor = last_screenshots[i]

            # Compare the current screenshot with the last captured one for this monitor.
            if not is_similar(current_screenshot, last_screenshot_for_monitor):
                last_screenshots[i] = current_screenshot  # ORIGINAL COMMENT: Update the last screenshot for this monitor

                # Convert NumPy array to PIL Image for saving.
                image = Image.fromarray(current_screenshot)
                timestamp = int(time.time()) # Get current Unix timestamp.
                # ORIGINAL COMMENT: Add monitor index to filename for uniqueness
                filename = f"{timestamp}_{i}.webp"
                filepath = os.path.join(screenshots_path, filename)

                # Save the image in WebP format (lossless).
                image.save(
                    filepath,
                    format="webp",
                    lossless=True,
                )

                # Perform OCR on the new screenshot.
                text: str = extract_text_from_image(current_screenshot)

                # ORIGINAL COMMENT: Only proceed if OCR actually extracts text
                if text.strip(): # Check if the extracted text is not empty or just whitespace.
                    embedding: np.ndarray = get_embedding(text) # Generate embedding for the text.
                    # Get metadata about the currently active application and window.
                    active_app_name: str = get_active_app_name() or "Unknown App"
                    active_window_title: str = get_active_window_title() or "Unknown Title"

                    # Insert the processed data into the database.
                    # NOTE: This call includes `filename` as the last argument.
                    # This may differ from the `insert_entry` signature in `database.py` (which previously expected 5 arguments).
                    # This suggests `database.py` might need an update to store the filename.
                    insert_entry(
                        text, timestamp, embedding, active_app_name, active_window_title, filename # ORIGINAL COMMENT: Pass filename
                    )

        time.sleep(3) # ORIGINAL COMMENT: Wait before taking the next screenshot

    # This return statement is unreachable due to the infinite `while True` loop above.
    # It might be an artifact from previous code iterations.
    return screenshots # 'screenshots' is not defined in this scope; likely meant 'current_screenshots'.


# This appears to be a second, possibly older or alternative, version of record_screenshots_thread.
# As per user instruction, this will also be commented.
def record_screenshots_thread(): # No type hint for return, implies None.
    """
    (Alternative Version) Continuously records screenshots and processes them.

    This version also sets `TOKENIZERS_PARALLELISM`, captures screenshots,
    checks for user activity, and compares image similarity.
    However, it has some key differences and potential issues compared to the
    first version:
    - Simpler filename generation (no monitor index, potential for overwrites or data loss
      if multiple monitors are active and timestamps are very close).
    - Uses variables `current_screenshot` and `filename` within the loop that
      are not defined in its immediate scope if the code path is followed strictly
      (e.g. `extract_text_from_image(current_screenshot)` where `screenshot` is the loop variable,
       and `filename` in `insert_entry` is not defined).

    This function is also intended to run in an infinite loop.
    """
    # ORIGINAL COMMENT: TODO: fix the error from huggingface tokenizers
    # The TODO suggests an awareness of potential issues with tokenizers.
    import os # Local import, different from the module-level import in the first version.

    # Setting TOKENIZERS_PARALLELISM, similar to the first version.
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    last_screenshots = take_screenshots() # Initial baseline screenshots.

    while True: # Main recording loop.
        if not is_user_active():
            time.sleep(3) # Wait if user is inactive.
            continue

        # In this version, the variable is named `screenshots`.
        screenshots_list = take_screenshots() # Renamed to avoid conflict with the first version's 'screenshots' return for clarity in comments.

        # Loop through each captured screenshot.
        for i, screenshot_item in enumerate(screenshots_list): # Renamed loop variables for clarity.

            # Assumes `last_screenshots` has a corresponding item.
            # Potential IndexError if monitor count changed and `last_screenshots` isn't updated accordingly.
            if i >= len(last_screenshots): # Basic guard
                if i < len(screenshots_list):
                    last_screenshots.append(screenshots_list[i])
                continue

            last_screenshot_for_monitor = last_screenshots[i]

            if not is_similar(screenshot_item, last_screenshot_for_monitor):
                last_screenshots[i] = screenshot_item # Update baseline for this monitor.

                image = Image.fromarray(screenshot_item)
                timestamp = int(time.time())

                # Filename does not include monitor index 'i'.
                # This could lead to issues if multiple screenshots from different monitors
                # get the exact same timestamp, or if only the first screen's data is intended.
                current_filename = f"{timestamp}.webp" # Defined `current_filename`
                image_path = os.path.join(screenshots_path, current_filename)
                image.save(
                    image_path,
                    format="webp",
                    lossless=True,
                )

                # BUG: `current_screenshot` is used here, but the loop variable is `screenshot_item`.
                # This will likely raise an UnboundLocalError or NameError if `current_screenshot`
                # from a previous scope (if any) is not what's intended.
                # Assuming `screenshot_item` was intended: text_content = extract_text_from_image(screenshot_item)
                text_content: str = extract_text_from_image(screenshot_item) # Corrected to use loop variable

                # ORIGINAL COMMENT: Only proceed if OCR actually extracts text
                if text_content.strip():
                    embedding: np.ndarray = get_embedding(text_content)
                    active_app_name: str = get_active_app_name() or "Unknown App"
                    active_window_title: str = get_active_window_title() or "Unknown Title"

                    # BUG: `filename` is used here but not defined in this scope.
                    # `current_filename` was defined above for the image path.
                    # Assuming `current_filename` was intended for the database entry.
                    # NOTE: This call also includes a 6th argument (filename), potentially
                    # mismatching the `database.py` `insert_entry` signature.
                    insert_entry(
                        text_content, timestamp, embedding, active_app_name, active_window_title, current_filename # Corrected to use defined filename, ORIGINAL COMMENT: Pass filename
                    )

        time.sleep(3) # ORIGINAL COMMENT: Wait before taking the next screenshot
