import io
import os
import h5py
import base64
import numpy as np
from PIL import Image
import random
from read_heatmap import HeatMapTileLoader, get_heatmap_overlay
from tqdm import tqdm

# Root directory where slides are stored
S3_MOUNT_PATH = "/home/ubuntu/cp-lab-wsi-upload/wsi-and-heatmaps"
OUTPUT_DIR = "test_tiles"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

slide_name = "bma_test_slide"
slide_h5_path = os.path.join(S3_MOUNT_PATH, slide_name + ".h5")
heatmap_h5_path = os.path.join(S3_MOUNT_PATH, slide_name + "_heatmap.h5")

# Load heatmap data with dimension check
with h5py.File(heatmap_h5_path, "r") as f:
    heatmap_dataset = f["heatmap"]
    print(f"Heatmap dataset shape: {heatmap_dataset.shape}")

    # make sure heatmap dataset is a numpy array
    heatmap = np.array(heatmap_dataset)
    # Create heatmap tile loader
    heatmap_tile_loader = HeatMapTileLoader(np_heatmap=heatmap)
    heatmap_tile_loader.compute_heatmap()


def retrieve_tile_h5(h5_path, level, row, col):
    """Retrieve the tile from an HDF5 file given level, row, and col."""
    with h5py.File(h5_path, "r") as f:
        try:
            jpeg_string = f[str(level)][row, col]
            jpeg_string = base64.b64decode(jpeg_string)
            image = Image.open(io.BytesIO(jpeg_string))
            image.load()  # Ensure the image is loaded fully
            return image
        except Exception as e:
            print(f"Error retrieving tile at level {level}, row {row}, col {col}: {e}")
            raise e


def image_to_jpeg_string(image):
    """Convert a PIL image to JPEG byte string."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def save_random_tiles(num_tiles=10, alpha=0.5):
    """Randomly retrieve tiles and save them with heatmap overlay for visual debugging."""
    levels = [0, 1, 2]  # Example levels, adjust based on your dataset
    max_row, max_col = 10, 10  # Example max values, adjust based on your dataset

    for i in tqdm(range(num_tiles), desc="Saving tiles"):
        # Randomly choose level, row, and column
        level = random.choice(levels)
        row = random.randint(0, max_row)
        col = random.randint(0, max_col)

        try:
            # Retrieve the region tile from the slide
            region = retrieve_tile_h5(slide_h5_path, level, row, col)
            heatmap_image = heatmap_tile_loader.get_heatmap_image(level, row, col)

            # Convert region to numpy and overlay heatmap
            overlay_image = get_heatmap_overlay(
                np.array(region), heatmap_image, alpha=alpha
            )
            overlay_pil_image = Image.fromarray(overlay_image)

            # Save the overlay image to the test_tiles directory
            file_path = os.path.join(OUTPUT_DIR, f"tile_{level}_{row}_{col}.png")
            overlay_pil_image.save(file_path)
            print(f"Saved tile at level {level}, row {row}, col {col} to {file_path}")

        except Exception as e:
            print(f"Error processing tile at level {level}, row {row}, col {col}: {e}")


if __name__ == "__main__":
    save_random_tiles()
