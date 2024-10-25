from flask import Flask, send_file, request, jsonify, render_template_string
import openslide
from PIL import Image
import io

app = Flask(__name__)

# A list of slide paths
slides = {
    "Slide 1": "/media/hdd3/neo/test_slide_1.ndpi",
    "Slide 2": "/media/hdd3/neo/test_slide_2.ndpi",
    "Slide 3": "/media/hdd3/neo/test_slide_3.ndpi"
}

# Set an initial slide
current_slide = slides["Slide 1"]
slide = openslide.OpenSlide(current_slide)

@app.route('/tile/<int:level>/<int:x>/<int:y>/', methods=['GET'])
def get_tile(level, x, y):
    tile_size = 256  # OpenSeadragon default tile size
    openslide_level = slide.level_count - 1 - level
    tile_x = x * tile_size * (2 ** openslide_level)
    tile_y = y * tile_size * (2 ** openslide_level)

    try:
        region = slide.read_region((tile_x, tile_y), openslide_level, (tile_size, tile_size)).convert("RGB")
        img_io = io.BytesIO()
        region.save(img_io, format='JPEG', quality=90)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error serving tile: {e}")
        return "Tile not found", 404

@app.route('/change_slide/<slide_name>', methods=['POST'])
def change_slide(slide_name):
    global slide
    if slide_name in slides:
        slide = openslide.OpenSlide(slides[slide_name])
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
