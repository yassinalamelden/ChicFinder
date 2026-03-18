import streamlit as st
from frontend.pages import upload_page, results_page

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

# Application Navigation
if "page" not in st.session_state:
    st.session_state["page"] = "upload"

st.sidebar.title("ChicFinder 👗")
st.sidebar.write("Get outfit recommendations based on the **OutfitAI** research paper.")

if st.session_state["page"] == "upload":
    upload_page.show()
elif st.session_state["page"] == "results":
    results_page.show()

st.sidebar.divider()
st.sidebar.info("Powered by FastAPI, Streamlit, and GPT-4o.")
