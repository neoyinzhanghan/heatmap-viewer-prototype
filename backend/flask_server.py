from flask import (
    Flask,
    send_file,
    request,
    jsonify,
    render_template_string,
    make_response,
)
from flask_cors import CORS
from PIL import Image
import h5py
import io
import numpy as np
import os
import base64
from read_heatmap import HeatMapTileLoader

app = Flask(__name__)
CORS(app)

# Configuration
S3_MOUNT_PATH = "/home/ubuntu/cp-lab-wsi-upload/wsi-and-heatmaps"
TILE_SIZE = 512
DEFAULT_ALPHA = 0.5

# Fixed test slide configuration
SLIDE_NAME = "bma_test_slide"
slide_h5_path = os.path.join(S3_MOUNT_PATH, f"{SLIDE_NAME}.h5")
heatmap_h5_path = os.path.join(S3_MOUNT_PATH, f"{SLIDE_NAME}_heatmap.h5")

# open the slide h5 file and get all the keys
with h5py.File(slide_h5_path, "r") as f:
    height = int(f["level_0_height"][()])
    width = int(f["level_0_width"][()])

# Global variables
alpha = DEFAULT_ALPHA

# Initialize heatmap on startup
with h5py.File(heatmap_h5_path, "r") as f:
    heatmap = np.array(f["heatmap"])
    heatmap_tile_maker = HeatMapTileLoader(np_heatmap=heatmap, tile_size=TILE_SIZE)
    heatmap_tile_maker.compute_heatmap()


def retrieve_tile_h5(h5_path, level, row, col):
    """Retrieve tile from an HDF5 file."""
    with h5py.File(h5_path, "r") as f:
        jpeg_string = base64.b64decode(f[str(level)][row, col])
        image = Image.open(io.BytesIO(jpeg_string))
        return image


def get_heatmap_overlay(region, heatmap_image, alpha=0.5):
    """Create overlay of region and heatmap."""
    heatmap_image = np.array(heatmap_image.convert("RGB"))
    region = region.astype(np.float32) / 255.0
    heatmap_image = heatmap_image.astype(np.float32) / 255.0
    heatmap_image = heatmap_image[: region.shape[0], : region.shape[1]]
    overlay_image_np = (1 - alpha) * region + alpha * heatmap_image
    return (np.clip(overlay_image_np, 0, 1) * 255).astype(np.uint8)


@app.route("/tile/<int:level>/<int:x>/<int:y>/", methods=["GET"])
def get_tile(level, x, y):
    try:
        region = retrieve_tile_h5(slide_h5_path, level, x, y)
        heatmap_image = heatmap_tile_maker.get_heatmap_image(level, x, y)
        overlay_image = get_heatmap_overlay(
            np.array(region), heatmap_image, alpha=alpha
        )
        img_io = io.BytesIO()
        Image.fromarray(overlay_image).save(img_io, format="JPEG", quality=90)
        img_io.seek(0)
        response = make_response(send_file(img_io, mimetype="image/jpeg"))
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        return response
    except Exception as e:
        print(f"Error serving tile: {e}")
        return f"Tile not found: {str(e)}", 404


@app.route("/set_alpha", methods=["POST"])
def set_alpha():
    global alpha
    alpha = float(request.json.get("alpha", DEFAULT_ALPHA))
    return jsonify(success=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
