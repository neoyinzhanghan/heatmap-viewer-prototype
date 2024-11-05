import io
import os
import h5py
import base64
import numpy as np
from PIL import Image
from flask import Flask, send_file, abort, Response, request
from flask_cors import CORS
from read_heatmap import HeatMapTileLoader, get_heatmap_overlay

app = Flask(__name__)
CORS(app)

# Root directory where slides are stored
S3_MOUNT_PATH = "/home/ubuntu/cp-lab-wsi-upload/wsi-and-heatmaps"


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


@app.route("/tile/<int:level>/<int:x>/<int:y>/", methods=["GET"])
def load_tile(level, x, y, slide_name="bma_test_slide"):
    """Load and overlay heatmap tile with region tile."""
    alpha = float(request.args.get("alpha", 0.5))
    slide_h5_path = os.path.join(S3_MOUNT_PATH, slide_name + ".h5")
    heatmap_h5_path = os.path.join(S3_MOUNT_PATH, slide_name + "_heatmap.h5")

    try:
        # Load heatmap data with dimension check
        with h5py.File(heatmap_h5_path, "r") as f:
            heatmap_dataset = f["heatmap"]
            print(f"Heatmap dataset shape: {heatmap_dataset.shape}")

            # make sure heatmap dataset is a numpy array
            heatmap = np.array(heatmap_dataset)

            # Create heatmap tile loader
            heatmap_tile_loader = HeatMapTileLoader(np_heatmap=heatmap)

        # Retrieve the tile region from the slide
        region = retrieve_tile_h5(slide_h5_path, level, x, y)
        heatmap_image = heatmap_tile_loader.get_heatmap_image(level, x, y)

        # Convert region to numpy and overlay heatmap
        overlay_image = get_heatmap_overlay(
            np.array(region), heatmap_image, alpha=alpha
        )
        overlay_pil_image = Image.fromarray(overlay_image)

        # Save to buffer and return as PNG
        img_io = io.BytesIO()
        overlay_pil_image.save(img_io, "PNG")
        img_io.seek(0)
        return Response(img_io, mimetype="image/png")

    except Exception as e:
        print(f"Error processing tile at level {level}, x {x}, y {y}: {e}")
        return f"Error processing tile: {e}", 500


@app.route("/tiles/<slide_name>/<int:level>/<int:x>/<int:y>.jpg")
def serve_tile(slide_name, level, x, y):
    """Serve a tile as a JPEG image."""
    slide_h5_path = os.path.join(S3_MOUNT_PATH, f"{slide_name}.h5")
    try:
        tile_image = retrieve_tile_h5(slide_h5_path, level, x, y)
        jpeg_bytes = image_to_jpeg_string(tile_image)

        img_io = io.BytesIO(jpeg_bytes)
        img_io.seek(0)
        return send_file(img_io, mimetype="image/jpeg")
    except Exception as e:
        print(
            f"Error serving tile for {slide_name} at level {level}, x {x}, y {y}: {e}"
        )
        abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
