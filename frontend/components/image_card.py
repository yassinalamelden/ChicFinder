import streamlit as st
from typing import Dict

def image_card(item: Dict):
    """
    reusable card component for fashion items.
    Displays image, category, brand, and price.
    """
    with st.container():
        st.image(item.get("image_url", ""), use_container_width=True)
        st.subheader(f"{item.get('brand', 'Generic')} - {item.get('category')}")
        st.write(f"Color: {item.get('color')} | Style: {item.get('style')}")
        if item.get("price"):
            st.write(f"**Price: ${item.get('price'):.2f}**")
        else:
            st.write("**Price: N/A**")
        st.button("View Item", key=f"btn_{item.get('id')}")
