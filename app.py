from flask import Flask, send_file, request, jsonify, render_template_string
from compute_heatmap import HeatMapTileMaker
from utils import smooth_function
from PIL import Image
import openslide
import io
import numpy as np
import os

app = Flask(__name__)

# Directory for uploaded slides
UPLOAD_FOLDER = "uploaded_slides"

# Helper function to get the full path of a slide
def get_slide_path(slide_name):
    return os.path.join(UPLOAD_FOLDER, slide_name)

# Set a default slide and initialize HeatMapTileMaker
current_slide = get_slide_path("/media/hdd3/neo/default_slide.ndpi")  # Change to an actual default slide path if needed
slide = openslide.OpenSlide(current_slide)

# Create an instance of HeatMapTileMaker and compute the heatmap once
heatmap_tile_maker = HeatMapTileMaker(slide_path=current_slide, tile_size=256)
heatmap_tile_maker.compute_heatmap()  # Assume this is a blocking method

@app.route('/tile/<int:level>/<int:x>/<int:y>/', methods=['GET'])
def get_tile(level, x, y):
    tile_size = 256  # OpenSeadragon default tile size
    openslide_level = slide.level_count - 1 - level
    tile_x = x * tile_size * (2 ** openslide_level)
    tile_y = y * tile_size * (2 ** openslide_level)

    try:
        # Read the region from the slide
        region = slide.read_region((tile_x, tile_y), openslide_level, (tile_size, tile_size)).convert("RGB")
        
        # Get the heatmap value for the given level, x, and y
        heatmap_value = heatmap_tile_maker.get_heatmap_values(level, x, y)
        heatmap_value = smooth_function(heatmap_value)  # Ensure a minimum heatmap value of 0.5

        print(f"Heatmap value: {heatmap_value}")

        # Ensure the heatmap value is a float
        if not isinstance(heatmap_value, (float, np.floating)):
            raise ValueError("Heatmap value is not a float")

        # Convert the region to a NumPy array and ensure it is of type float32
        region = np.array(region, dtype=np.float32) / 255.0  # Normalize the pixel values to [0, 1]

        # Multiply each pixel value by the heatmap value (between 0 and 1)
        region *= heatmap_value  # Apply heatmap multiplier
        region = np.clip(region * 255.0, 0, 255).astype(np.uint8)  # Convert back to uint8 for image representation

        # Convert the modified region back to an image
        region_image = Image.fromarray(region)

        # Save the image to a BytesIO object to serve it
        img_io = io.BytesIO()
        region_image.save(img_io, format='JPEG', quality=90)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error serving tile: {e}")
        return "Tile not found", 404


@app.route('/change_slide/<slide_name>', methods=['POST'])
def change_slide(slide_name):
    global slide, heatmap_tile_maker
    slide_path = get_slide_path(slide_name)
    if os.path.exists(slide_path):
        slide = openslide.OpenSlide(slide_path)
        
        # Reinitialize the heatmap tile maker for the new slide
        heatmap_tile_maker = HeatMapTileMaker(slide_path=slide_path, tile_size=256)
        heatmap_tile_maker.compute_heatmap()  # Assume this is a blocking method
        
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
