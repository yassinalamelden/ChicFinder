import streamlit as st
from utils.api_client import APIClient

def show():
    """file uploader + trigger button for outfit recommendations."""
    st.header("Upload Your Outfit")
    st.write("Upload a photo of your outfit to get personalized recommendations.")
    
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        if st.button("Get Recommendations"):
            client = APIClient()
            with st.spinner("Analyzing outfit and finding matches..."):
                try:
                    recommendations = client.get_recommendations(uploaded_file.getvalue())
                    st.session_state["recommendations"] = recommendations
                    st.session_state["page"] = "results"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error fetching recommendations: {e}")
