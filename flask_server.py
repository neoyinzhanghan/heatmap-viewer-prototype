import os
import h5py
import io
import numpy as np
import glob
import base64
import threading
import time
import boto3
from flask import Flask, send_file, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allows requests from any origin
os.environ["AWS_SHARED_CREDENTIALS_FILE"] = "/home/ubuntu/.aws_alt/credentials"

# Configuration
S3_MOUNT_PATH = "/home/ubuntu/cp-lab-wsi-upload/wsi-and-heatmaps"
TILE_SIZE = 256
DEFAULT_ALPHA = 0.2
INACTIVITY_TIMEOUT = 1800  # Time in seconds before shutdown

# Load environment variables from .env file
load_dotenv()
INSTANCE_ID = os.getenv("INSTANCE_ID")
AWS_REGION = os.getenv("AWS_REGION")

# Global variables
alpha = DEFAULT_ALPHA
last_activity_time = time.time()  # Track last API call time
heatmap_tile_makers = {}  # Dictionary to store heatmap tile makers per slide


@app.route("/")
def home():
    return "Welcome to the Heatmap Viewer!"


def update_last_activity():
    """Update the last activity timestamp."""
    global last_activity_time
    last_activity_time = time.time()


def shutdown_ec2_instance():
    """Shut down the EC2 instance if inactive for too long."""
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    print("Shutting down EC2 instance due to inactivity.")
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])


def monitor_inactivity():
    """Monitor for inactivity and shut down if exceeded."""
    while True:
        time.sleep(5)  # Check every 5 seconds
        if time.time() - last_activity_time > INACTIVITY_TIMEOUT:
            shutdown_ec2_instance()
            break


# Start the inactivity monitor thread
monitor_thread = threading.Thread(target=monitor_inactivity)
monitor_thread.daemon = True
monitor_thread.start()


@app.route("/slides", methods=["GET"])
def list_slides():
    """Endpoint to list all available slides (.h5 files)"""
    try:
        h5_files = glob.glob(os.path.join(S3_MOUNT_PATH, "*.h5"))
        slide_names = [os.path.basename(f).replace(".h5", "") for f in h5_files]
        return jsonify(slides=slide_names)
    except Exception as e:
        print(f"Error listing slides: {e}")
        return jsonify(error="Could not retrieve slide list"), 500


@app.route("/dimensions", methods=["GET"])
def get_dimensions():
    """Endpoint to retrieve slide dimensions based on selected slide name."""
    slide_name = request.args.get("slide")
    if not slide_name:
        return jsonify(error="Slide name is required"), 400

    slide_h5_path = os.path.join(S3_MOUNT_PATH, f"{slide_name}.h5")
    if not os.path.exists(slide_h5_path):
        return jsonify(error="Slide not found"), 404

    try:
        with h5py.File(slide_h5_path, "r") as f:
            height = int(f["level_0_height"][()])
            width = int(f["level_0_width"][()])
        return jsonify(height=height, width=width)
    except Exception as e:
        print(f"Error reading dimensions for slide '{slide_name}': {e}")
        return jsonify(error="Could not retrieve slide dimensions"), 500


@app.route("/tile/<string:slide>/<int:level>/<int:x>/<int:y>/", methods=["GET"])
def get_tile(slide, level, x, y):
    """Retrieve a tile for a specific slide and apply the heatmap overlay."""
    slide_h5_path = os.path.join(S3_MOUNT_PATH, f"{slide}.h5")
    heatmap_h5_path = os.path.join(S3_MOUNT_PATH, "heatmaps", f"{slide}_heatmap.h5")

    # Validate file existence
    if not os.path.exists(slide_h5_path):
        return "Slide not found", 404
    if not os.path.exists(heatmap_h5_path):
        return "Heatmap not found", 404

    try:
        # Retrieve slide and heatmap tiles
        slide_tile = retrieve_tile_h5(slide_h5_path, level, x, y)
        heatmap_tile = retrieve_tile_h5(heatmap_h5_path, level, x, y)

        if slide_tile is None or heatmap_tile is None:
            return "Tile not found", 404

        # Apply the overlay
        overlay_image = get_heatmap_overlay(
            np.array(slide_tile.convert("RGB")), heatmap_tile, alpha=alpha
        )

        # Convert overlay to image and send response
        img_io = io.BytesIO()
        Image.fromarray(overlay_image).save(img_io, format="JPEG", quality=90)
        img_io.seek(0)
        response = make_response(send_file(img_io, mimetype="image/jpeg"))
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        return response
    except Exception as e:
        print(
            f"Error serving tile at level {level}, row {x}, col {y} for slide '{slide}': {e}"
        )
        return jsonify({"error": f"Tile not found: {str(e)}"}), 404


def retrieve_tile_h5(h5_path, level, row, col):
    """Retrieve tile from an HDF5 file."""
    try:
        with h5py.File(h5_path, "r") as f:
            jpeg_string = base64.b64decode(f[str(level)][row, col])
            image = Image.open(io.BytesIO(jpeg_string))
            return image
    except Exception as e:
        print(f"Error retrieving tile at level {level}, row {row}, col {col}: {e}")
        return None


def get_heatmap_overlay(region, heatmap_image, alpha=0.5):
    """Create overlay of region and heatmap."""
    heatmap_image = np.array(heatmap_image.convert("RGB"))
    region = region.astype(np.float32) / 255.0
    heatmap_image = heatmap_image.astype(np.float32) / 255.0
    heatmap_image = heatmap_image[: region.shape[0], : region.shape[1]]
    overlay_image_np = (1 - alpha) * region + alpha * heatmap_image
    return (np.clip(overlay_image_np, 0, 1) * 255).astype(np.uint8)


@app.route("/set_alpha", methods=["POST"])
def set_alpha():
    """Set the transparency level for the overlay."""
    update_last_activity()
    global alpha
    try:
        alpha_value = request.json.get("alpha", DEFAULT_ALPHA)
        alpha = float(alpha_value)
        print(f"Alpha set to: {alpha}")
        return jsonify(success=True)
    except (TypeError, ValueError) as e:
        print(f"Error setting alpha: {e}")
        return jsonify(success=False, error=str(e)), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # No SSL
