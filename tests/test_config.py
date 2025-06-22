"""
Tests for the `openrecall.config` module.

This test suite focuses on verifying the behavior of the `get_appdata_folder`
function under different simulated operating system environments (Windows, macOS, Linux)
and conditions (e.g., missing environment variables). It uses `pytest` for test
organization and `unittest.mock` for patching system attributes and environment
variables to simulate these different environments. The `tmp_path` fixture from
pytest is used to create temporary directories for testing path creation.
"""
import pytest
from unittest import mock
from openrecall.config import get_appdata_folder # Function to be tested.


def test_get_appdata_folder_windows(tmp_path):
    """
    Tests `get_appdata_folder` behavior on a simulated Windows environment.

    It mocks `sys.platform` to "win32" and the `APPDATA` environment variable.
    Verifies that the function constructs the correct path within the mocked
    `APPDATA` directory and that the directory is created.

    Args:
        tmp_path: pytest fixture for a temporary directory path.
    """
    # Simulate Windows environment.
    with mock.patch("sys.platform", "win32"):
        # Mock the APPDATA environment variable to point to the temporary path.
        with mock.patch.dict("os.environ", {"APPDATA": str(tmp_path)}):
            # Define the expected path structure on Windows.
            expected_path = tmp_path / "openrecall"
            # Call the function and assert the returned path is as expected.
            assert get_appdata_folder() == str(expected_path)
            # Assert that the directory was actually created by the function.
            assert expected_path.exists()


def test_get_appdata_folder_windows_no_appdata():
    """
    Tests `get_appdata_folder` behavior on Windows when APPDATA is not set.

    It mocks `sys.platform` to "win32" and ensures `APPDATA` is not in
    the environment variables. Verifies that an `EnvironmentError` is raised,
    as expected by the function's design.
    """
    # Simulate Windows environment.
    with mock.patch("sys.platform", "win32"):
        # Ensure APPDATA is not present in the mocked environment.
        with mock.patch.dict("os.environ", {}, clear=True):
            # Expect an EnvironmentError to be raised with a specific message.
            with pytest.raises(
                EnvironmentError, match="APPDATA environment variable is not set."
            ):
                get_appdata_folder()


def test_get_appdata_folder_darwin(tmp_path):
    """
    Tests `get_appdata_folder` behavior on a simulated macOS (darwin) environment.

    Mocks `sys.platform` to "darwin" and `os.path.expanduser` to return
    the temporary path (simulating the user's home directory).
    Verifies the correct path construction within `~/Library/Application Support/`
    and that the directory is created.

    Args:
        tmp_path: pytest fixture for a temporary directory path.
    """
    # Simulate macOS environment.
    with mock.patch("sys.platform", "darwin"):
        # Mock os.path.expanduser to control the "home" directory.
        with mock.patch("os.path.expanduser", return_value=str(tmp_path)):
            # Define the expected path structure on macOS.
            expected_path = tmp_path / "Library" / "Application Support" / "openrecall"
            # Call the function and assert path correctness and existence.
            assert get_appdata_folder() == str(expected_path)
            assert expected_path.exists()


def test_get_appdata_folder_linux(tmp_path):
    """
    Tests `get_appdata_folder` behavior on a simulated Linux environment.

    Mocks `sys.platform` to "linux" and `os.path.expanduser` to return
    the temporary path. Verifies the correct path construction within
    `~/.local/share/` and that the directory is created.

    Args:
        tmp_path: pytest fixture for a temporary directory path.
    """
    # Simulate Linux environment.
    with mock.patch("sys.platform", "linux"):
        # Mock os.path.expanduser for home directory control.
        with mock.patch("os.path.expanduser", return_value=str(tmp_path)):
            # Define the expected path structure on Linux.
            expected_path = tmp_path / ".local" / "share" / "openrecall"
            # Call the function and assert path correctness and existence.
            assert get_appdata_folder() == str(expected_path)
            assert expected_path.exists()
