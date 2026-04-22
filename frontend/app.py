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

# Custom Styling (Chic Minimalist CSS)
st.markdown("""
<style>
    /* Global font */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Elegant Headers */
    h1 {
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: 3rem !important;
        letter-spacing: -0.5px;
        text-align: center;
        margin-bottom: 0.5rem !important;
    }
    h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        letter-spacing: 0.5px;
    }
    
    /* Subtitle styling */
    .subtitle {
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 4px;
        padding: 0.5rem 2rem;
        font-weight: 500;
        letter-spacing: 0.5px;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Top bar adjustment */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    /* File Uploader Container */
    [data-testid="stFileUploadDropzone"] {
        border-radius: 8px;
        transition: border-color 0.3s ease;
    }
    
    /* Upload Button inside Uploader */
    [data-testid="stFileUploadDropzone"] button {
        border-radius: 4px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("✨ ChicFinder")
st.sidebar.markdown(
    """<div style='color: #666; font-size: 0.9rem; margin-bottom: 20px;'>
    AI-powered personal styling and fashion discovery.
    </div>""", unsafe_allow_html=True
)
st.sidebar.divider()
st.sidebar.write("Get outfit recommendations based on the **OutfitAI** research paper. Upload an item, and let our engine retrieve similar pieces instantly.")

st.sidebar.divider()
st.sidebar.info("Powered by FastAPI, FAISS, and Streamlit.")

# Hero Section
st.markdown("<h1>ChicFinder</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Discover fashion that matches your style instantly.</div>", unsafe_allow_html=True)
st.write("---")

upload_container = st.container()
with upload_container:
    uploaded_file = st.file_uploader("Upload an inspiration photo (Drag & Drop)", type=["jpg", "jpeg", "png"])
    
    with st.expander("⚙️ Advanced Filters (Optional)"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            price_range = st.slider("Price Range (EGP)", 0, 10000, (0, 10000), step=50)
        with col_f2:
            brand_options = ["Tomato Store", "Town Team", "Mobaco"]
            selected_brands = st.multiselect("Select Brands", brand_options, default=[])

if uploaded_file is not None:
    st.write("---")
    # Layout with left column for image, right for actions/results
    col_img, col_actions = st.columns([1, 1.5], gap="large")
    
    with col_img:
        st.markdown("### Your Inspiration")
        st.image(uploaded_file, use_container_width=True)
    
    with col_actions:
        st.markdown("### Action")
        st.write("Ready to find similar items in our catalog?")
        launch_search = st.button("✨ Discover Similar Pieces", use_container_width=True)
        
    if launch_search:
        st.write("---")

        
        with st.spinner("Analyzing outfit and finding matches..."):
            try:
                # 1. Read the file bytes and encode to base64 string
                base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
                
                # 2. Create the exact JSON payload our FastAPI expects
                payload = {
                    "image_base64": base64_image,
                    "min_price": price_range[0],
                    "max_price": price_range[1]
                }
                if selected_brands:
                    payload["brands"] = selected_brands
                
                # 3. Send POST request to the /api/v1/search endpoint we just fixed
                response = requests.post("http://localhost:8000/api/v1/search", json=payload)
                response.raise_for_status()
                
                # 4. Get the response data
                data = response.json()
                
            except Exception as e:
                st.error(f"Backend is currently unreachable or returned an error: {e}")
                data = {}
                
            # 5. Render the results 
            # (Make sure your render_results function expects the {"results": [...]} dictionary format!)
            if data:
                render_results(data)