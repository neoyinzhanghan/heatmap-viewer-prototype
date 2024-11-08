import os
import h5py
import io
import numpy as np
import os
import base64
import threading
import time
import boto3
from read_heatmap import HeatMapTileLoader  # Ensure this module is accessible
from flask import Flask, send_file, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allows requests from any origin
os.environ["AWS_SHARED_CREDENTIALS_FILE"] = "/home/ubuntu/.aws_alt/credentials"


# Configuration
S3_MOUNT_PATH = "/home/ubuntu/cp-lab-wsi-upload/wsi-and-heatmaps"
TILE_SIZE = 512
DEFAULT_ALPHA = 0.5
INACTIVITY_TIMEOUT = 10  # Time in seconds before shutdown

# Load environment variables from .env file
load_dotenv()
# AWS Configuration
INSTANCE_ID = os.getenv("INSTANCE_ID")
AWS_REGION = os.getenv("AWS_REGION")
# Fixed test slide configuration
SLIDE_NAME = "bma_test_slide"
slide_h5_path = os.path.join(S3_MOUNT_PATH, f"{SLIDE_NAME}.h5")
heatmap_h5_path = os.path.join(S3_MOUNT_PATH, "heatmaps", f"{SLIDE_NAME}_heatmap.h5")

# Global variables
alpha = DEFAULT_ALPHA
last_activity_time = time.time()  # Track last API call time


# Initialize slide dimensions and heatmap
try:
    with h5py.File(slide_h5_path, "r") as f:
        height = int(f["level_0_height"][()])
        width = int(f["level_0_width"][()])
    print(f"Loaded slide dimensions: height={height}, width={width}")
except Exception as e:
    print(f"Error reading slide dimensions: {e}")
    height, width = None, None

try:
    with h5py.File(heatmap_h5_path, "r") as f:
        heatmap = np.array(f["heatmap"])
        heatmap_tile_maker = HeatMapTileLoader(np_heatmap=heatmap, tile_size=TILE_SIZE)
        heatmap_tile_maker.compute_heatmap()
    print("Heatmap initialized successfully")
except Exception as e:
    print(f"Error loading heatmap: {e}")
    heatmap_tile_maker = None


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


@app.route("/dimensions", methods=["GET"])
def get_dimensions():
    """Endpoint to retrieve slide dimensions."""
    update_last_activity()
    if not height or not width:
        return jsonify(error="Slide dimensions not set"), 500
    return jsonify(height=height, width=width)


@app.route("/")
def index():
    """Root endpoint for testing."""
    update_last_activity()
    return "Flask server is running", 200


@app.route("/tile/<int:level>/<int:x>/<int:y>/", methods=["GET"])
def get_tile(level, x, y):
    """Retrieve a tile and apply the heatmap overlay."""
    update_last_activity()
    if not height or not width:
        return "Slide dimensions not set", 500
    if not heatmap_tile_maker:
        return "Heatmap not initialized", 500

    try:
        region = retrieve_tile_h5(slide_h5_path, level, x, y)
        if region is None:
            return "Tile not found", 404

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
        print(f"Error serving tile at level {level}, row {x}, col {y}: {e}")
        return f"Tile not found: {str(e)}", 404


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
    app.run(debug=True, host="0.0.0.0", port=5000)
