import streamlit as st
import requests

# List of slide names (you can make this dynamic by reading from a directory or database)
slide_options = ["Slide 1", "Slide 2", "Slide 3"]

# Streamlit sidebar to select slides
st.sidebar.title("Slide Gallery")
selected_slide = st.sidebar.selectbox("Select a slide", slide_options)

# Send request to Flask server to change the slide
if st.sidebar.button("Load Slide"):
    response = requests.post(f"http://127.0.0.1:5000/change_slide/{selected_slide}")
    if response.ok:
        st.success(f"Successfully changed to {selected_slide}")
    else:
        st.error(f"Failed to change slide to {selected_slide}")

st.write("Use the OpenSeadragon viewer below to interact with the selected slide.")
st.markdown(f"""
    <iframe src="http://127.0.0.1:5000" width="100%" height="600px"></iframe>
""", unsafe_allow_html=True)
