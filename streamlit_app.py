import requests
import streamlit as st

# List of available slides
slide_options = {
    "Test Slide 1": "/media/hdd3/neo/test_slide_1.ndpi",
    "Test Slide 2": "/media/hdd3/neo/test_slide_2.ndpi",
    "Test Slide 3": "/media/hdd3/neo/test_slide_3.ndpi"
}

# Streamlit sidebar for selecting slides
st.sidebar.title("Slide Selection")
selected_slide_name = st.sidebar.selectbox("Choose a slide", list(slide_options.keys()))
slide_uploaded = False

# Submit button to process the selected slide
if st.sidebar.button("Submit Slide"):
    selected_slide_path = slide_options[selected_slide_name].split("/")[-1]
    
    # Send the selected slide to the Flask server
    try:
        response = requests.post(f"http://127.0.0.1:5000/change_slide/{selected_slide_path}")
        if response.ok:
            st.sidebar.success(f"Slide {selected_slide_name} is now loaded.")
            slide_uploaded = True
        else:
            st.sidebar.error(f"Failed to load slide {selected_slide_name}. Server error.")
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Failed to connect to server: {e}")

# Alpha slider
if slide_uploaded:
    alpha = st.sidebar.slider("Overlay Transparency (Alpha)", min_value=0.0, max_value=1.0, value=0.5, step=0.05)
    st.session_state.alpha = alpha

    # Send alpha value to the server whenever it changes
    try:
        response = requests.post(f"http://127.0.0.1:5000/set_alpha", json={"alpha": alpha})
        if not response.ok:
            st.error("Failed to update transparency setting.")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to server: {e}")

    st.write("Use the OpenSeadragon viewer below to interact with the selected slide.")
    st.markdown(f"""
        <iframe src="http://127.0.0.1:5000" width="100%" height="600px"></iframe>
    """, unsafe_allow_html=True)
