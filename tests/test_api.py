import requests
import sys

# Define the base URL for the OpenRecall application
BASE_URL = "http://localhost:8082"

def test_search_endpoint(query="test query"):
    """
    Tests the /search endpoint of the OpenRecall API.
    """
    search_url = f"{BASE_URL}/search"
    params = {"q": query}

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        print(f"Successfully connected to {search_url}")
        print(f"Status Code: {response.status_code}")

        # Basic check for HTML content indicating results might be present
        if "<div class=\"card\">" in response.text and "<img src=\"/static/" in response.text:
            print("Search results page seems to be structured as expected.")
            return True
        elif "Nothing recorded yet" in response.text:
            print("Server responded, but no data has been recorded yet. This is a valid state.")
            return True
        elif "Search" in response.text and not query: # Case where query is empty, still a valid page
             print(f"Search page loaded, but the query was empty: '{query}'")
             return True
        else:
            print("Search results page content does not match expected structure.")
            # print("\nFirst 500 characters of response text:")
            # print(response.text[:500]) # Optionally print part of the response for debugging
            return False

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to the server at {BASE_URL}.")
        print("Please ensure the OpenRecall application (openrecall/app.py) is running.")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    # You can run this script with a command-line argument for the query
    # Example: python tests/test_api.py "my search term"
    search_query = "test"  # Default query
    if len(sys.argv) > 1:
        search_query = sys.argv[1]

    print(f"Testing search endpoint with query: '{search_query}'")
    if test_search_endpoint(search_query):
        print("\nTest passed (or server responded correctly for empty data state).")
    else:
        print("\nTest failed.")
