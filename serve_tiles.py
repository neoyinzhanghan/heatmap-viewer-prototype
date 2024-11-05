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


def image_to_jpeg_string(image):
    # Create an in-memory bytes buffer
    buffer = io.BytesIO()
    try:
        # Save the image in JPEG format to the buffer
        image.save(buffer, format="JPEG")
        jpeg_string = buffer.getvalue()  # Get the byte data
    finally:
        buffer.close()  # Explicitly close the buffer to free memory

    return jpeg_string


def jpeg_string_to_image(jpeg_string):
    # Create an in-memory bytes buffer from the byte string
    buffer = io.BytesIO(jpeg_string)

    # Open the image from the buffer and keep the buffer open
    image = Image.open(buffer)

    # Load the image data into memory so that it doesn't depend on the buffer anymore
    image.load()

    return image


def encode_image_to_base64(jpeg_string):
    return base64.b64encode(jpeg_string)


def decode_image_from_base64(encoded_string):
    return base64.b64decode(encoded_string)


def retrieve_tile_h5(h5_path, level, row, col):
    with h5py.File(h5_path, "r") as f:
        try:
            jpeg_string = f[str(level)][row, col]
            jpeg_string = decode_image_from_base64(jpeg_string)
            image = jpeg_string_to_image(jpeg_string)

        except Exception as e:
            print(
                f"Error: {e} occurred while retrieving tile at level: {level}, row: {row}, col: {col} from {h5_path}"
            )
            jpeg_string = f[str(level)][row, col]
            print(f"jpeg_string: {jpeg_string}")
            jpeg_string = decode_image_from_base64(jpeg_string)
            print(f"jpeg_string base 64 decoded: {jpeg_string}")
            raise e
        return image


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
