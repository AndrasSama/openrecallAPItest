"""
Natural Language Processing (NLP) utilities for OpenRecall.

This module provides functionalities for generating text embeddings using
SentenceTransformer models and for calculating cosine similarity between
these embeddings. It aims to convert textual content into numerical vectors
that capture semantic meaning, which can then be used for tasks like
semantic search or content comparison.

The module pre-loads a specified SentenceTransformer model on initialization
to optimize performance by avoiding repeated model loading.
"""
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

# ORIGINAL COMMENT: Configure logging
# Set up basic logging configuration for the module.
# Messages will be logged at the INFO level and above.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Get a logger instance specific to this module.

# ORIGINAL COMMENT: Constants
MODEL_NAME: str = "all-MiniLM-L6-v2" # Specifies the pre-trained model to be used for embeddings.
EMBEDDING_DIM: int = 384  # ORIGINAL COMMENT: Dimension for all-MiniLM-L6-v2
                          # This is the dimensionality of the embedding vectors produced by the MODEL_NAME.
                          # It's important this matches the actual output dimension of the chosen model.

# ORIGINAL COMMENT: Load the model globally to avoid reloading it on every call
# This attempts to load the SentenceTransformer model when the module is first imported.
# Storing it in a global variable `model` makes it readily available to functions
# like `get_embedding` without the overhead of loading it each time.
model: Optional[SentenceTransformer] = None # Initialize model as None before attempting to load.
try:
    model = SentenceTransformer(MODEL_NAME)
    logger.info(f"SentenceTransformer model '{MODEL_NAME}' loaded successfully.")
except Exception as e:
    # If model loading fails (e.g., model not found, network issues, dependency problems),
    # log the error and keep `model` as None. Functions using the model should handle this.
    logger.error(f"Failed to load SentenceTransformer model '{MODEL_NAME}': {e}")
    model = None # Explicitly set to None on failure.


def get_embedding(text: str) -> np.ndarray:
    """
    ORIGINAL COMMENT: Generates a sentence embedding for the given text.

    ORIGINAL COMMENT: Splits the text into lines, encodes each line using the pre-loaded
    ORIGINAL COMMENT: SentenceTransformer model, and returns the mean of the embeddings.
    ORIGINAL COMMENT: Handles empty input text by returning a zero vector.

    This function processes the input text by first splitting it into individual lines.
    Each non-empty line is then encoded into an embedding vector. The final embedding
    for the entire text is the arithmetic mean of these line embeddings. This approach
    provides a single vector representation for a potentially multi-line input.

    If the global `model` failed to load during module initialization, or if the input
    text is empty or contains only whitespace, this function returns a zero vector
    of the predefined `EMBEDDING_DIM`.

    Args:
        text (str): The input string to embed. Can be multi-line.

    Returns:
        np.ndarray: A NumPy array of type `np.float32` representing the mean
                    embedding of the text lines. If the input text is effectively
                    empty, or if the model is not available, a zero vector of
                    shape (`EMBEDDING_DIM`,) is returned.
    """
    if model is None:
        # Log an error if the model wasn't loaded and return a zero vector.
        logger.error("SentenceTransformer model is not loaded. Returning zero vector.")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    if not text or text.isspace():
        # Handle empty or whitespace-only input by logging a warning and returning a zero vector.
        logger.warning("Input text is empty or whitespace. Returning zero vector.")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    # ORIGINAL COMMENT: Split text into non-empty lines
    # This filters out any lines that are empty or contain only whitespace after stripping.
    sentences = [line for line in text.split("\n") if line.strip()]

    if not sentences:
        # If, after filtering, there are no valid sentences, log a warning and return a zero vector.
        logger.warning("No non-empty lines found after splitting. Returning zero vector.")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    try:
        # Encode all valid sentences using the pre-loaded SentenceTransformer model.
        # This typically returns a list of NumPy arrays (or a 2D NumPy array).
        sentence_embeddings = model.encode(sentences, convert_to_numpy=True)
        # ORIGINAL COMMENT: Calculate the mean embedding
        # Compute the mean of the sentence embeddings along axis 0 (column-wise mean for a 2D array).
        # Ensure the result is of dtype float32.
        mean_embedding = np.mean(sentence_embeddings, axis=0, dtype=np.float32)
        return mean_embedding
    except Exception as e:
        # If any error occurs during the encoding or mean calculation process, log the error
        # and return a zero vector as a fallback.
        logger.error(f"Error generating embedding for text (first 50 chars): '{text[:50]}': {e}")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    ORIGINAL COMMENT: Calculates the cosine similarity between two numpy vectors.

    Cosine similarity measures the cosine of the angle between two non-zero vectors,
    providing a measure of similarity in direction, irrespective of magnitude.
    It ranges from -1 (exactly opposite) to 1 (exactly the same), with 0 indicating orthogonality.

    Args:
        a (np.ndarray): The first numpy array (vector).
        b (np.ndarray): The second numpy array (vector).
                        Both `a` and `b` are expected to be 1D arrays of the same dimension.

    Returns:
        float: The cosine similarity score, a float between -1.0 and 1.0.
               Returns 0.0 if either input vector has zero magnitude (norm),
               as cosine similarity is undefined in such cases.
    """
    # Calculate the L2 norm (magnitude) of vector a.
    norm_a = np.linalg.norm(a)
    # Calculate the L2 norm (magnitude) of vector b.
    norm_b = np.linalg.norm(b)

    # If either vector has zero magnitude, their dot product is zero,
    # and cosine similarity is undefined (or can be taken as 0).
    # This check prevents division by zero.
    if norm_a == 0 or norm_b == 0:
        logger.warning("One or both vectors have zero magnitude. Cosine similarity is undefined; returning 0.0.")
        return 0.0

    # Calculate the dot product of vectors a and b.
    dot_product = np.dot(a, b)
    # Calculate cosine similarity using the formula: (a . b) / (||a|| * ||b||)
    similarity = dot_product / (norm_a * norm_b)

    # ORIGINAL COMMENT: Clip values to handle potential floating-point inaccuracies slightly outside [-1, 1]
    # Due to floating-point arithmetic, the similarity score might slightly exceed the [-1, 1] range.
    # np.clip ensures the value stays within these bounds.
    return float(np.clip(similarity, -1.0, 1.0))
