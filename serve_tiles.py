import io
import os
import h5py
import numpy as np
from PIL import Image
from flask import Flask, send_file, abort, Response, request
from flask_cors import CORS
from compute_heatmap import HeatMapTileLoader, get_heatmap_overlay
from LLRunner.slide_processing.dzsave_h5 import retrieve_tile_h5


app = Flask(__name__)
CORS(app)

# Root directory where slides are stored
S3_MOUNT_PATH = "/home/ubuntu/cp-lab-wsi-upload/wsi-and-heatmaps"


@app.route("/tile/<int:level>/<int:x>/<int:y>/", methods=["GET"])
def load_tile(level, x, y, slide_name="bma_test_slide"):
    alpha = float(
        request.args.get("alpha", 0.5)
    )  # Get alpha from query, default to 0.5
    slide_h5_path = os.path.join(S3_MOUNT_PATH, slide_name + ".h5")
    heatmap_h5_path = os.path.join(S3_MOUNT_PATH, slide_name + "_heatmap.h5")

    # Load heatmap data
    with h5py.File(heatmap_h5_path, "r") as f:
        heatmap = f["heatmap"][level, x, y]
        heatmap_tile_loader = HeatMapTileLoader(np_heatmap=heatmap)

    try:
        # Retrieve the tile region from the slide
        region = retrieve_tile_h5(slide_h5_path, level, x, y)
        heatmap_image = heatmap_tile_loader.get_heatmap_image(level, x, y)

        # Convert the PIL region image to a numpy array
        region = np.array(region)

        # Overlay the heatmap on the region with specified transparency
        overlay_image = get_heatmap_overlay(region, heatmap_image, alpha=alpha)

        # Convert the resulting overlay image back to a PIL image
        overlay_pil_image = Image.fromarray(overlay_image)

        # Save to an in-memory file
        img_io = io.BytesIO()
        overlay_pil_image.save(img_io, "PNG")
        img_io.seek(0)

        # Return the image as a response
        return Response(img_io, mimetype="image/png")

    except Exception as e:
        return f"Error processing tile: {e}", 500


@app.route("/tiles/<slide_name>/<int:level>/<int:x>/<int:y>.jpg")
def serve_tile(slide_name, level, x, y):
    tile_path = load_tile(slide_name, level, x, y)
    if tile_path:
        return send_file(tile_path, mimetype="image/jpeg")
    else:
        abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
