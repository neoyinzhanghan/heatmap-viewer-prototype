import os
import requests
import streamlit as st

# Directory to store uploaded slides
UPLOAD_FOLDER = "uploaded_slides"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# List existing slides
def get_slides():
    return [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".ndpi")]

# Streamlit sidebar to select slides
st.sidebar.title("Slide Gallery")

# Upload slide feature
uploaded_file = st.sidebar.file_uploader("Upload a slide (.ndpi)", type="ndpi")
if uploaded_file:
    # Save the uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Successfully uploaded {uploaded_file.name}")

# Display available slides for selection
slide_options = get_slides()
selected_slide = st.sidebar.selectbox("Select a slide", slide_options)

# Slider to adjust alpha value
alpha = st.sidebar.slider("Overlay Transparency (Alpha)", min_value=0.0, max_value=1.0, value=0.5, step=0.05)

# Send alpha value to the server
if selected_slide:
    st.session_state.alpha = alpha
    response = requests.post(f"http://127.0.0.1:5000/change_slide/{selected_slide}", json={"alpha": alpha})
    if response.ok:
        st.sidebar.success(f"Successfully changed to {selected_slide} with alpha={alpha}")
    else:
        st.sidebar.error(f"Failed to change slide to {selected_slide}")

st.write("Use the OpenSeadragon viewer below to interact with the selected slide.")
st.markdown(f"""
    <iframe src="http://127.0.0.1:5000" width="100%" height="600px"></iframe>
""", unsafe_allow_html=True)
