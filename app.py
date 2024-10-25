from flask import Flask, send_file, request, jsonify, render_template_string
from compute_heatmap import HeatMapTileMaker
from utils import smooth_function
from PIL import Image
import openslide
import io
import numpy as np
import os

app = Flask(__name__)

# Transparency of the overlay (default value)
alpha = 0.5
# Directory for uploaded slides
UPLOAD_FOLDER = "uploaded_slides"

# Helper function to get the full path of a slide
def get_slide_path(slide_name):
    return os.path.join(UPLOAD_FOLDER, slide_name)

# Create a placeholder variable for the slide
slide = None
heatmap_tile_maker = None

def get_heatmap_overlay(region, heatmap_image, alpha=0.5):
    # (Same function as before to blend images)
    heatmap_image = np.array(heatmap_image.convert("RGB"))
    if region.shape[2] != 3:
        raise ValueError("Region image must be in RGB format with 3 channels")
    region = region.astype(np.float32) / 255.0
    heatmap_image = heatmap_image.astype(np.float32) / 255.0
    overlay_image_np = (1 - alpha) * region + alpha * heatmap_image
    overlay_image_np = np.clip(overlay_image_np, 0, 1)
    overlay_image_np = (overlay_image_np * 255).astype(np.uint8)
    return Image.fromarray(overlay_image_np)


@app.route('/tile/<int:level>/<int:x>/<int:y>/', methods=['GET'])
def get_tile(level, x, y):
    if not slide:
        return "No slide loaded", 400

    tile_size = 256
    openslide_level = slide.level_count - 1 - level
    tile_x = x * tile_size * (2 ** openslide_level)
    tile_y = y * tile_size * (2 ** openslide_level)

    try:
        region = slide.read_region((tile_x, tile_y), openslide_level, (tile_size, tile_size)).convert("RGB")
        heatmap_image = heatmap_tile_maker.get_heatmap_image(level, x, y)
        region = np.array(region, dtype=np.uint8)
        overlay_image = get_heatmap_overlay(region, heatmap_image, alpha=alpha)
        img_io = io.BytesIO()
        overlay_image.save(img_io, format='JPEG', quality=90)
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
        heatmap_tile_maker = HeatMapTileMaker(slide_path=slide_path, tile_size=256)
        heatmap_tile_maker.compute_heatmap()  # Assume this is a blocking method
        return jsonify(success=True)
    return jsonify(success=False), 400

@app.route('/set_alpha', methods=['POST'])
def set_alpha():
    global alpha
    alpha = request.json.get("alpha", 0.5)
    return jsonify(success=True)

@app.route('/')
def index():
    if not slide:
        return "No slide loaded", 400

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

                window.onload = function() {
                    viewer.world.removeAll();
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
            </script>
        </body>
    </html>
    """, height_value=slide.dimensions[1], width_value=slide.dimensions[0], max_level=slide.level_count - 1)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
