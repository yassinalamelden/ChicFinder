import streamlit as st
from frontend.components.image_card import image_card

def show():
    """grid of recommended items."""
    st.header("Recommended Items")
    
    if "recommendations" not in st.session_state:
        st.warning("No recommendations found. Please upload an outfit first.")
        if st.button("Go to Upload"):
            st.session_state["page"] = "upload"
            st.rerun()
        return

    recommendations = st.session_state["recommendations"]
    
    for rec in recommendations:
        query_item = rec.get("query_item", {})
        st.subheader(f"Recommendations for: {query_item.get('style')} {query_item.get('color')} {query_item.get('type')}")
        
        cols = st.columns(3)
        for i, item in enumerate(rec.get("recommendations", [])):
            with cols[i % 3]:
                image_card(item)

    if st.button("Start New Search"):
        del st.session_state["recommendations"]
        st.session_state["page"] = "upload"
        st.rerun()
