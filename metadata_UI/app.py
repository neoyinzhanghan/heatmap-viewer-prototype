from flask import Flask, jsonify, request
import pandas as pd

app = Flask(__name__)

# Load metadata
METADATA_PATH = (
    "/home/dog/Documents/neo/cp-lab-wsi-upload/wsi-and-heatmaps/pancreas_metadata.csv"
)
metadata = pd.read_csv(METADATA_PATH)


@app.route("/")
def index():
    """Serve the main page with inline HTML and JavaScript."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WSI Metadata Viewer</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    </head>
    <body>
        <h1>WSI Metadata Viewer</h1>
        <table id="metadataTable" class="display">
            <thead>
                <tr>
                    <th>Filename</th>
                    <th>Heatmap Filename</th>
                    <th>Pseudo Index</th>
                    <th>Old Filename</th>
                    <th>Old Heatmap Filename</th>
                    <th>Case Name</th>
                    <th>Benign Probability</th>
                    <th>Low Grade Probability</th>
                    <th>Malignant Probability</th>
                    <th>Non-diagnosis Probability</th>
                    <th>Label</th>
                    <th>Split</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
        <button id="selectRowBtn">Select Row</button>
        <p id="selectedRowDetails"></p>

        <script>
            $(document).ready(function () {
                // Fetch metadata and populate the table
                $.getJSON('/get_metadata', function (data) {
                    const table = $('#metadataTable').DataTable({
                        data: data,
                        columns: [
                            { data: 'filename' },
                            { data: 'heatmap_filename' },
                            { data: 'pseudo_idx' },
                            { data: 'old_filename' },
                            { data: 'old_heatmap_filename' },
                            { data: 'case_name' },
                            { data: 'benign_prob' },
                            { data: 'low_grade_prob' },
                            { data: 'malignant_prob' },
                            { data: 'non_diagnosis_prob' },
                            { data: 'label' },
                            { data: 'split' }
                        ]
                    });

                    // Handle row selection
                    $('#metadataTable tbody').on('click', 'tr', function () {
                        $(this).toggleClass('selected');
                    });

                    // Handle row selection button click
                    $('#selectRowBtn').click(function () {
                        const selectedData = table.rows('.selected').data();
                        if (selectedData.length > 0) {
                            const selectedRow = selectedData[0]; // Get the first selected row
                            $('#selectedRowDetails').text(
                                `Selected Filename: ${selectedRow.filename}, Heatmap Filename: ${selectedRow.heatmap_filename}`
                            );

                            // Optionally send to server
                            $.ajax({
                                url: '/select_slide',
                                method: 'POST',
                                contentType: 'application/json',
                                data: JSON.stringify(selectedRow),
                                success: function (response) {
                                    console.log(response.message);
                                }
                            });
                        } else {
                            alert('No row selected!');
                        }
                    });
                });
            });
        </script>
    </body>
    </html>
    """


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
