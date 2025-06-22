"""
Tests for the `openrecall.nlp.cosine_similarity` function.

This test suite uses `pytest` to verify the correctness of the
`cosine_similarity` function under various conditions, including:
- Identical vectors.
- Orthogonal vectors.
- Opposite vectors.
- Non-unit vectors.
- Arbitrary vectors.
- Vectors including a zero vector.

It uses `numpy` for vector creation and `pytest.approx` for comparing
floating-point results.
"""
import pytest
import numpy as np
from openrecall.nlp import cosine_similarity # Function to be tested.


def test_cosine_similarity_identical_vectors():
    """
    Tests cosine similarity with two identical vectors.
    Expected result is 1.0, indicating perfect similarity.
    """
    a = np.array([1, 0, 0], dtype=np.float32)
    b = np.array([1, 0, 0], dtype=np.float32)
    assert cosine_similarity(a, b) == 1.0, "Cosine similarity of identical vectors should be 1.0"


def test_cosine_similarity_orthogonal_vectors():
    """
    Tests cosine similarity with two orthogonal vectors.
    Expected result is 0.0.
    """
    a = np.array([1, 0, 0], dtype=np.float32)
    b = np.array([0, 1, 0], dtype=np.float32)
    assert cosine_similarity(a, b) == 0.0, "Cosine similarity of orthogonal vectors should be 0.0"


def test_cosine_similarity_opposite_vectors():
    """
    Tests cosine similarity with two directly opposite vectors.
    Expected result is -1.0.
    """
    a = np.array([1, 0, 0], dtype=np.float32)
    b = np.array([-1, 0, 0], dtype=np.float32)
    assert cosine_similarity(a, b) == -1.0, "Cosine similarity of opposite vectors should be -1.0"


def test_cosine_similarity_non_unit_vectors():
    """
    Tests cosine similarity with non-unit vectors that are in the same direction.
    Expected result is 1.0, as cosine similarity is independent of magnitude.
    """
    a = np.array([3, 0, 0], dtype=np.float32) # Vector a with magnitude 3
    b = np.array([1, 0, 0], dtype=np.float32) # Vector b with magnitude 1
    assert cosine_similarity(a, b) == 1.0, "Cosine similarity of parallel non-unit vectors should be 1.0"


def test_cosine_similarity_arbitrary_vectors():
    """
    Tests cosine similarity with two arbitrary non-trivial vectors.
    The expected result is calculated manually using the dot product and norms,
    and then compared using `pytest.approx` for floating-point precision.
    """
    a = np.array([1, 2, 3], dtype=np.float32)
    b = np.array([4, 5, 6], dtype=np.float32)
    # Manual calculation of expected cosine similarity: (a . b) / (||a|| * ||b||)
    expected_similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    assert cosine_similarity(a, b) == pytest.approx(expected_similarity), \
        "Cosine similarity of arbitrary vectors does not match expected value."


def test_cosine_similarity_zero_vector():
    """
    Tests cosine similarity when one of the input vectors is a zero vector.

    The `cosine_similarity` function in `openrecall.nlp` is designed to return 0.0
    if either vector has zero magnitude (to prevent division by zero). This test
    verifies this behavior.

    Note: The original test asserted `np.isnan(result)`. This comment and assertion
    have been updated to reflect the current implementation of `cosine_similarity`
    which returns 0.0 in this case, not NaN.
    """
    a = np.array([0, 0, 0], dtype=np.float32) # Zero vector
    b = np.array([1, 0, 0], dtype=np.float32) # Non-zero vector
    result = cosine_similarity(a, b)
    # The nlp.cosine_similarity function returns 0.0 if a norm is 0.
    assert result == 0.0, \
        "Expected result to be 0.0 when one of the vectors is a zero vector, as per current implementation."
    # ORIGINAL COMMENT: assert np.isnan(
    # ORIGINAL COMMENT:     result
    # ORIGINAL COMMENT: ), "Expected result to be NaN when one of the vectors is a zero vector"
