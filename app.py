from flask import Flask, send_file, request, jsonify, render_template_string
from compute_heatmap import HeatMapTileMaker
from utils import smooth_function
from PIL import Image
import openslide
import io
import numpy as np
import os

app = Flask(__name__)

alpha = 0.5  # Transparency of the overlay (default value)
# Directory for uploaded slides
UPLOAD_FOLDER = "uploaded_slides"

# Helper function to get the full path of a slide
def get_slide_path(slide_name):
    return os.path.join(UPLOAD_FOLDER, slide_name)

white_image = Image.new("RGB", (256, 256), (255, 255, 255))

# Set a default slide and initialize HeatMapTileMaker
current_slide = get_slide_path("/media/hdd3/neo/default_slide.ndpi")  # Change to an actual default slide path if needed
slide = openslide.OpenSlide(current_slide)

# Create an instance of HeatMapTileMaker and compute the heatmap once
heatmap_tile_maker = HeatMapTileMaker(slide_path=current_slide, tile_size=256)
heatmap_tile_maker.compute_heatmap()  # Assume this is a blocking method


def get_heatmap_overlay(region, heatmap_image, alpha=0.5):
    """
    Overlays a heatmap image onto the original region.

    Parameters:
    - region (numpy.ndarray): The original region image in RGB format.
    - heatmap_image (PIL.Image.Image): The heatmap image to overlay in RGB format.
    - alpha (float): The blending weight for the heatmap overlay (default is 0.5).
    
    Returns:
    - overlay_image (PIL.Image.Image): The resulting image with the overlay.
    """

    # Convert the heatmap image from PIL to a NumPy array (assume it's in RGB)
    heatmap_image = np.array(heatmap_image.convert("RGB"))  # Convert to NumPy array if needed

    # Ensure that region is in RGB format and is a NumPy array
    if region.shape[2] != 3:  # Ensure the region has three channels (RGB)
        raise ValueError("Region image must be in RGB format with 3 channels")

    # Normalize the region and heatmap images to range [0, 1]
    region = region.astype(np.float32) / 255.0
    heatmap_image = heatmap_image.astype(np.float32) / 255.0

    # Blend the images using alpha
    overlay_image_np = (1 - alpha) * region + alpha * heatmap_image

    # Clip values to ensure they are in range [0, 1]
    overlay_image_np = np.clip(overlay_image_np, 0, 1)

    # Convert the result back to an 8-bit image and then to a PIL image
    overlay_image_np = (overlay_image_np * 255).astype(np.uint8)
    overlay_image = Image.fromarray(overlay_image_np)

    return overlay_image



@app.route('/tile/<int:level>/<int:x>/<int:y>/', methods=['GET'])
def get_tile(level, x, y):
    tile_size = 256  # OpenSeadragon default tile size
    openslide_level = slide.level_count - 1 - level
    tile_x = x * tile_size * (2 ** openslide_level)
    tile_y = y * tile_size * (2 ** openslide_level)

    try:
        # Read the region from the slide
        region = slide.read_region((tile_x, tile_y), openslide_level, (tile_size, tile_size)).convert("RGB")
        
        # Get the heatmap image for the given level, x, and y
        heatmap_image = heatmap_tile_maker.get_heatmap_image(level, x, y)  # Assuming this returns a NumPy array between 0 and 1

        # Convert the region to a NumPy array (in BGR format for OpenCV)
        region = np.array(region, dtype=np.uint8)

        # Apply the overlay using the heatmap image
        overlay_image = get_heatmap_overlay(region, heatmap_image, alpha=alpha)

        # Save the image to a BytesIO object to serve it
        img_io = io.BytesIO()
        overlay_image.save(img_io, format='JPEG', quality=90)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error serving tile: {e}")
        return "Tile not found", 404


@app.route('/change_slide/<slide_name>', methods=['POST'])
def change_slide(slide_name):
    global slide, heatmap_tile_maker, alpha
    slide_path = get_slide_path(slide_name)
    if os.path.exists(slide_path):
        slide = openslide.OpenSlide(slide_path)

        # Reinitialize the heatmap tile maker for the new slide
        heatmap_tile_maker = HeatMapTileMaker(slide_path=slide_path, tile_size=256)
        heatmap_tile_maker.compute_heatmap()  # Assume this is a blocking method
        
        # Update alpha value if provided in the request
        alpha = request.json.get("alpha", 0.5)

        return jsonify(success=True)
    return jsonify(success=False), 400

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
        <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/2.4.2/openseadragon.min.js"></script>
        </head>
        <body>
            <div id="openseadragon1" style="width: 800px; height: 600px;"></div>
            <script type="text/javascript">
                var viewer = OpenSeadragon({
                    id: "openseadragon1",
                    prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/2.4.2/images/",
                    tileSources: {
                        height: {{ height_value }},
                        width: {{ width_value }},
                        tileSize: 256,
                        minLevel: 0,
                        maxLevel: {{ max_level }},
                        getTileUrl: function(level, x, y) {
                            return "/tile/" + level + "/" + x + "/" + y + "/";
                        }
                    }
                });

                // Function to reload the viewer when a new slide is selected
                function refreshViewer() {
                    viewer.world.removeAll();  // Clear existing tiles
                    viewer.open({
                        height: {{ height_value }},
                        width: {{ width_value }},
                        tileSize: 256,
                        minLevel: 0,
                        maxLevel: {{ max_level }},
                        getTileUrl: function(level, x, y) {
                            return "/tile/" + level + "/" + x + "/" + y + "/";
                        }
                    });
                }

                // Automatically refresh the viewer every time the page loads
                window.onload = function() {
                    refreshViewer();
                }
            </script>
        </body>
    </html>
    """, height_value=slide.dimensions[1], width_value=slide.dimensions[0], max_level=slide.level_count - 1)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
