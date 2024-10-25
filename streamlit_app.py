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

# Alpha slider for overlay transparency
alpha = st.sidebar.slider("Initial Overlay Transparency (Alpha)", min_value=0.0, max_value=1.0, value=0.5, step=0.05)

# Submit button to process the selected slide
if st.sidebar.button("Submit Slide"):
    selected_slide_path = slide_options[selected_slide_name].split("/")[-1]
    
    # Send the selected slide and alpha value to the Flask server
    try:
        # Send slide selection request
        response_slide = requests.post(f"http://127.0.0.1:5000/change_slide/{selected_slide_path}")
        if response_slide.ok:
            # Send alpha value request
            response_alpha = requests.post(f"http://127.0.0.1:5000/set_alpha", json={"alpha": alpha})
            if response_alpha.ok:
                st.sidebar.success(f"Slide {selected_slide_name} is now loaded with alpha {alpha}.")
                slide_uploaded = True
            else:
                st.sidebar.error("Failed to set transparency. Server error.")
        else:
            st.sidebar.error(f"Failed to load slide {selected_slide_name}. Server error.")
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Failed to connect to server: {e}")

# Display OpenSeadragon viewer if the slide is uploaded
if slide_uploaded:
    st.write("Use the OpenSeadragon viewer below to interact with the selected slide.")
    
    # Use Streamlit container and a responsive iframe to fit the entire viewer
    viewer_height = 800  # Adjust height dynamically based on your needs
    
    st.markdown(f"""
        <iframe src="http://127.0.0.1:5000" width="100%" height="{viewer_height}px" style="border:none; display:block; margin:0 auto;"></iframe>
    """, unsafe_allow_html=True)
