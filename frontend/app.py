import streamlit as st
import requests
import base64
from frontend.results_gallery import render_results

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
        # Convert image to Base64 encoding
        base64_str = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        
        # Strip "data:image/...;base64," prefix if it exists
        if ";base64," in base64_str:
            base64_str = base64_str.split(";base64,")[-1]
            
        payload = {"image": base64_str}
        
        st.divider()
        
        with st.spinner("Analyzing outfit and finding matches..."):
            try:
                # 1. Update API Endpoint
                # Ensure requests are sent to http://localhost:8000/search via POST
                response = requests.post("http://localhost:8000/search", json=payload)
                response.raise_for_status()
                data = response.json()
            except Exception:
                st.warning("Backend is currently unreachable. Switching to mock test data.")
                
                # Mock API response works perfectly for local testing
                data = {
                    "processing_time_ms": 210.3,
                    "results": [
                        {
                            "image_id": "test_local_01",
                            "similarity_score": 0.91,
                            "brand": "Defacto",
                            "price_egp": 650.00,
                            "product_url": "https://www.defacto.com/eg-en/example",
                            "store_location": "City Stars",
                            "availability_egypt": True
                        }
                    ]
                }
                
            render_results(data)
