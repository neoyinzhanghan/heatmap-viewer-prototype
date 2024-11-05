import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Define the URL of your Flask server
BASE_URL = "http://localhost:8080"  # Update if necessary
VIEWER_ENDPOINT = "/tile/1/0/0/?alpha=0.5"  # Example tile URL for testing

# Set up Chrome options (you can also use Firefox or another browser)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode for testing

# Path to ChromeDriver (change this if necessary)
service = Service(
    "path/to/chromedriver"
)  # Ensure the driver is in your PATH or specify the full path


def test_wsi_viewer_tile_loading():
    # Initialize the WebDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Navigate to the WSI viewer tile URL
        driver.get(f"{BASE_URL}{VIEWER_ENDPOINT}")

        # Wait for the image tile to load
        wait = WebDriverWait(driver, 10)
        tile_image = wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))

        # Check if the image source is loaded
        img_src = tile_image.get_attribute("src")
        if img_src:
            print("Test passed: Tile image loaded successfully.")
        else:
            print("Test failed: Tile image did not load.")

    except Exception as e:
        print(f"Error during test: {e}")

    finally:
        # Close the browser
        driver.quit()


# Run the test
if __name__ == "__main__":
    print("Running WSI viewer tile loading test...")
    test_wsi_viewer_tile_loading()
