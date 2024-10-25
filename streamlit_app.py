import os
import requests
import streamlit as st

# Directory to store uploaded slides
UPLOAD_FOLDER = "uploaded_slides"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Streamlit sidebar for uploading slides
st.sidebar.title("Slide Upload")

# Upload slide feature
uploaded_file = st.sidebar.file_uploader("Upload a slide (.ndpi)", type="ndpi")
if uploaded_file:
    # Save the uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Successfully uploaded {uploaded_file.name}")

    # Send the uploaded slide to the Flask server
    response = requests.post(f"http://127.0.0.1:5000/change_slide/{uploaded_file.name}")
    if response.ok:
        st.success(f"Slide {uploaded_file.name} is now loaded.")
    else:
        st.error(f"Failed to load slide {uploaded_file.name}")

# Alpha slider
alpha = st.sidebar.slider("Overlay Transparency (Alpha)", min_value=0.0, max_value=1.0, value=0.5, step=0.05)
st.session_state.alpha = alpha

# Send alpha value to the server whenever it changes
response = requests.post(f"http://127.0.0.1:5000/set_alpha", json={"alpha": alpha})
if not response.ok:
    st.error("Failed to update transparency setting.")

st.write("Use the OpenSeadragon viewer below to interact with the selected slide.")
st.markdown(f"""
    <iframe src="http://127.0.0.1:5000" width="100%" height="600px"></iframe>
""", unsafe_allow_html=True)
