import streamlit as st
import requests
import base64
from results_gallery import render_results

st.set_page_config(
    page_title="ChicFinder - Outfit Recommendation Expert",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Vanilla CSS)
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
        color: #212529;
    }
    .stButton>button {
        background-color: #007bff;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("ChicFinder 👗")
st.sidebar.write("Get outfit recommendations based on the **OutfitAI** research paper.")

st.sidebar.divider()
st.sidebar.info("Powered by FastAPI, Streamlit, and GPT-4o.")

st.title("Upload Your Outfit")
st.write("Upload a photo of your outfit to get personalized recommendations.")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
    
    if st.button("Get Recommendations"):
        st.divider()
        
        with st.spinner("Analyzing outfit and finding matches..."):
            try:
                # 1. Update API Endpoint
                # Endpoint is /api/v1/recommend, and uses multipart/form-data
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post("http://localhost:8000/api/v1/recommend", files=files)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                st.error(f"Backend is currently unreachable or returned an error: {e}")
                data = {}
                
            render_results(data)
