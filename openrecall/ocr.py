"""
Optical Character Recognition (OCR) module for OpenRecall.

This module utilizes the `doctr` library to perform OCR on images,
extracting textual content. It pre-loads a specific pre-trained OCR model
for efficiency. The extracted text is structured by concatenating words
with spaces and adding newlines to approximate original line and block structure.
"""
from doctr.models import ocr_predictor
from PIL.Image import Image as PILImage # For type hinting, assuming PIL/Pillow Image
import numpy as np # For type hinting, assuming NumPy array

# Initialize the OCR predictor model from the `doctr` library.
# This model is loaded once when the module is imported, making it readily
# available for subsequent OCR tasks without reloading.
ocr = ocr_predictor(
    pretrained=True,  # Use pre-trained weights for the model.
    det_arch="db_mobilenet_v3_large",  # Specifies the detection model architecture.
                                      # 'db_mobilenet_v3_large' is a common choice for good accuracy and speed.
    reco_arch="crnn_mobilenet_v3_large", # Specifies the recognition model architecture.
                                       # 'crnn_mobilenet_v3_large' is often paired with the detection model.
)


def extract_text_from_image(image: any) -> str:
    """
    Extracts text from a given image using the pre-loaded doctr OCR model.

    The function processes the image and iterates through the hierarchical
    structure of the OCR result (pages, blocks, lines, words) to reconstruct
    the textual content. Words are separated by spaces, lines by single
    newlines, and blocks by double newlines.

    Args:
        image (any): The input image to perform OCR on. This should be in a
                     format compatible with the `doctr.models.ocr_predictor`,
                     typically a NumPy array (H, W, C) or a PIL Image.

    Returns:
        str: The extracted text content from the image. If no text is found,
             an empty string is returned. The text is formatted with spaces
             between words and newlines to reflect basic structure.
    """
    # The ocr predictor expects a list of images.
    # The result object contains the OCR output structured hierarchically.
    result = ocr([image])

    extracted_text_parts = [] # Use a list to build parts of the text for efficiency

    # Iterate through each page in the OCR result (typically one for a single image).
    for page in result.pages:
        # Iterate through each block of text identified on the page.
        for block in page.blocks:
            # Iterate through each line of text within the block.
            for line in block.lines:
                line_text_parts = [] # Collect words for the current line
                # Iterate through each word recognized in the line.
                for word in line.words:
                    line_text_parts.append(word.value) # Append the string value of the word.
                # Join words in the line with a space and add a newline character at the end of the line.
                if line_text_parts:
                    extracted_text_parts.append(" ".join(line_text_parts))
            # Add an extra newline character after each block to separate blocks of text.
            # This helps in preserving some of the spatial layout of the original text.
            if block.lines: # Only add block separator if there were lines in the block
                extracted_text_parts.append("") # Represents a newline for block separation in the final join

    # Join all parts with a newline. Double newlines (from empty strings for block separators)
    # will create the visual separation between blocks.
    return "\n".join(extracted_text_parts)
