from flask import Flask, jsonify, request, render_template
import pandas as pd

app = Flask(__name__)

# Load metadata
METADATA_PATH = "/home/ubuntu/cp-lab-wsi-upload/wsi-and-heatmaps/pancreas_metadata.csv"
metadata = pd.read_csv(METADATA_PATH)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_metadata", methods=["GET"])
def get_metadata():
    """Serve the metadata as JSON."""
    data = metadata.to_dict(orient="records")
    return jsonify(data)


@app.route("/select_slide", methods=["POST"])
def select_slide():
    """Handle the selected slide."""
    selected_row = request.json
    print(f"Selected Row: {selected_row}")
    return jsonify({"message": "Slide selected", "selected_row": selected_row})


if __name__ == "__main__":
    app.run(debug=True)
