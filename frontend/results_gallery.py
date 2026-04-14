import streamlit as st
import os

def render_results(api_response: dict):
    """
    Safely parses the API response and renders the results gallery.
    Handles missing fields gracefully to prevent KeyErrors.
    """
    st.header("Search Results")
    
    if not api_response:
        st.warning("No response received from the server.")
        return
        
    outfit_items = api_response.get("recommendations", [])
    
    if not outfit_items:
        st.info("No matching outfits found.")
        return
        
    for item_group in outfit_items:
        query_item = item_group.get("query_item", {})
        item_type = query_item.get("type", "Item")
        description = query_item.get("description", "")
        
        st.subheader(f"Matches for: {item_type}")
        if description:
            st.caption(description)
            
        group_recs = item_group.get("recommendations", [])
        
        cols = st.columns(3)
        for i, rec in enumerate(group_recs):
            if not isinstance(rec, dict):
                continue
                
            with cols[i % 3]:
                with st.container():
                    # 1. Display Image
                    image_path_raw = rec.get("image_url", "")
                    
                    # Normalize path (Windows paths etc)
                    image_path = image_path_raw.replace("\\", "/")
                    
                    if image_path and os.path.exists(image_path):
                        st.image(image_path, use_container_width=True)
                    else:
                        st.write(f"📷 *Image locally unavailable ({rec.get('id')})*")
                        st.caption(f"Expected at: {image_path}")
                    
                    # 3. Brand
                    brand = rec.get("brand")
                    if brand:
                        st.write(f"**Brand:** {brand}")
                        
                    # 4. Price
                    price = rec.get("price")
                    if price is not None and price != "N/A":
                        st.write(f"**Price:** {price}")
                        
                    # 5. Category
                    category = rec.get("category")
                    if category:
                        st.write(f"**Category:** {category}")
                        
                    st.divider()
