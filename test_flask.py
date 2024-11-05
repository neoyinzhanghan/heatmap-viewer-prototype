from flask import (
    Flask,
    send_file,
    request,
    jsonify,
    render_template_string,
    make_response,
    abort,
    Response,
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
    height = f["level_0_height"]
    width = f["level_0_width"]

    # now extract the float values
    height = height[()]

    # now extract the float values
    width = width[()]
    print(height, width)

import sys

sys.exit()

# Global variables
alpha = DEFAULT_ALPHA

# Initialize heatmap on startup
with h5py.File(heatmap_h5_path, "r") as f:
    heatmap_dataset = f["heatmap"]
    heatmap = np.array(heatmap_dataset)
    heatmap_tile_maker = HeatMapTileLoader(np_heatmap=heatmap, tile_size=TILE_SIZE)
    heatmap_tile_maker.compute_heatmap()


def retrieve_tile_h5(h5_path, level, row, col):
    """Retrieve tile from an HDF5 file."""
    with h5py.File(h5_path, "r") as f:
        try:
            jpeg_string = f[str(level)][row, col]
            jpeg_string = base64.b64decode(jpeg_string)
            image = Image.open(io.BytesIO(jpeg_string))
            image.load()
            return image
        except Exception as e:
            print(f"Error retrieving tile at level {level}, row {row}, col {col}: {e}")
            raise e


def get_heatmap_overlay(region, heatmap_image, alpha=0.5):
    """Create overlay of region and heatmap."""
    heatmap_image = np.array(heatmap_image.convert("RGB"))
    if region.shape[2] != 3:
        raise ValueError("Region image must be in RGB format with 3 channels")

    region = region.astype(np.float32) / 255.0
    heatmap_image = heatmap_image.astype(np.float32) / 255.0
    overlay_image_np = (1 - alpha) * region + alpha * heatmap_image
    overlay_image_np = np.clip(overlay_image_np, 0, 1)
    overlay_image_np = (overlay_image_np * 255).astype(np.uint8)
    return overlay_image_np


@app.route("/tile/<int:level>/<int:x>/<int:y>/", methods=["GET"])
def get_tile(level, x, y):
    try:
        # Get the base tile
        region = retrieve_tile_h5(slide_h5_path, level, x, y)

        # Get heatmap overlay
        heatmap_image = heatmap_tile_maker.get_heatmap_image(level, x, y)

        # Create overlay
        region_np = np.array(region)
        overlay_image = get_heatmap_overlay(region_np, heatmap_image, alpha=alpha)
        overlay_pil = Image.fromarray(overlay_image)

        # Prepare response
        img_io = io.BytesIO()
        overlay_pil.save(img_io, format="JPEG", quality=90)
        img_io.seek(0)

        response = make_response(send_file(img_io, mimetype="image/jpeg"))
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        print(f"Error serving tile: {e}")
        return f"Tile not found: {str(e)}", 404


@app.route("/set_alpha", methods=["POST"])
def set_alpha():
    global alpha
    alpha = float(request.json.get("alpha", DEFAULT_ALPHA))
    return jsonify(success=True)


@app.route("/")
def index():
    # Fixed max level
    MAX_LEVEL = 18

    return render_template_string(
        """
        <!DOCTYPE html>
        <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/2.4.2/openseadragon.min.js"></script>
                <style>
                    body { font-family: Arial, sans-serif; }
                    .container {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        padding: 20px;
                    }
                    #openseadragon1 {
                        width: 800px;
                        height: 600px;
                        margin-bottom: 20px;
                    }
                    #alpha-slider { width: 800px; }
                    #apply-button {
                        margin-top: 10px;
                        padding: 5px 15px;
                        font-size: 16px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div id="openseadragon1"></div>
                    <label for="alpha-slider">Adjust Overlay Transparency:</label>
                    <input type="range" id="alpha-slider" min="0" max="1" step="0.01" value="0.5">
                    <button id="apply-button" onclick="applyNewTransparency()">Apply New Transparency</button>
                </div>
                <script type="text/javascript">
                    var viewer;

                    function initializeViewer() {
                        if (viewer) {
                            viewer.destroy();
                        }

                        viewer = OpenSeadragon({
                            id: "openseadragon1",
                            prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/2.4.2/images/",
                            tileSources: {
                                height: {{ height }},
                                width: {{ width }},
                                tileSize: {{ tile_size }},
                                minLevel: 0,
                                maxLevel: {{ max_level }},
                                getTileUrl: function(level, x, y) {
                                    return "/tile/" + level + "/" + x + "/" + y + "/?v=" + new Date().getTime();
                                }
                            },
                            showNavigator: true,
                            preserveViewport: true,
                            immediateRender: true,
                            useCanvas: true,
                            tileCache: null
                        });
                    }

                    function applyNewTransparency() {
                        var alphaValue = document.getElementById("alpha-slider").value;
                        fetch('/set_alpha', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ alpha: alphaValue }),
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                initializeViewer();
                            }
                        });
                    }

                    window.onload = function() {
                        initializeViewer();
                    }
                </script>
            </body>
        </html>
        """,
        height=height,
        width=width,
        max_level=MAX_LEVEL,
        tile_size=TILE_SIZE,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
