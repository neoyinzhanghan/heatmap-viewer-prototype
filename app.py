from flask import Flask, send_file, request
import openslide
from PIL import Image
import numpy as np
import io

app = Flask(__name__)

# Path to your NDPI slide
slide_path = "/media/hdd3/neo/BMA_AML/H19-5352;S1;MSKZ - 2023-12-12 01.47.31.ndpi"
slide = openslide.OpenSlide(slide_path)

@app.route('/tile/<int:level>/<int:x>/<int:y>/', methods=['GET'])
def get_tile(level, x, y):
    tile_size = 256  # OpenSeadragon default tile size
    # Calculate pixel coordinates for the requested tile
    tile_x = x * tile_size
    tile_y = y * tile_size

    # Read the region and return it as an image
    try:
        region = slide.read_region((tile_x, tile_y), level, (tile_size, tile_size)).convert("RGB")
        img_io = io.BytesIO()
        region.save(img_io, format='JPEG', quality=90)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error serving tile: {e}")
        return "Tile not found", 404

@app.route('/')
def index():
    return """
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
                        height: {height_value},
                        width: {width_value},
                        tileSize: 256,
                        minLevel: 0,
                        maxLevel: {max_level},
                        getTileUrl: function(level, x, y) {
                            return "/tile/" + level + "/" + x + "/" + y + "/";
                        }
                    }
                });
            </script>
        </body>
    </html>
    """.format(
        height_value=slide.dimensions[1],
        width_value=slide.dimensions[0],
        max_level=slide.level_count - 1
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
