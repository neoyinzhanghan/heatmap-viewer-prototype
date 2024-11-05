import requests

# Define the base URL for your local Flask server
BASE_URL = "http://127.0.0.1:8080"
TILE_ENDPOINT = "/tile/{level}/{x}/{y}/"
TEST_LEVEL = 1
TEST_X = 0
TEST_Y = 0
ALPHA_VALUE = 0.5  # Transparency level for overlay

def test_wsi_tile_loading(level, x, y, alpha):
    # Construct the full URL for the tile request
    url = f"{BASE_URL}{TILE_ENDPOINT.format(level=level, x=x, y=y)}"
    params = {"alpha": alpha}
    
    try:
        # Send a GET request to the server
        response = requests.get(url, params=params)
        
        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            print("Test passed: Tile image loaded successfully.")
            
            # Save the response content as an image file to verify output
            output_filename = f"test_output_level_{level}_x_{x}_y_{y}_alpha_{alpha}.png"
            with open(output_filename, "wb") as f:
                f.write(response.content)
            print(f"Image saved as '{output_filename}'")
        else:
            print(f"Test failed: Status code {response.status_code}, Message: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error during test request: {e}")

# Run the test
if __name__ == "__main__":
    print("Testing WSI tile loading...")
    test_wsi_tile_loading(TEST_LEVEL, TEST_X, TEST_Y, ALPHA_VALUE)
