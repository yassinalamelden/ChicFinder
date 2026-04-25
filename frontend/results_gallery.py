import streamlit as st
import os

def render_results(api_response: dict):
    """
    Safely parses the API response and renders the results gallery.
    Handles missing fields gracefully to prevent KeyErrors.
    """
    st.markdown("<h3>Curated Matches</h3>", unsafe_allow_html=True)
    
    if not api_response:
        st.warning("No response received from the server.")
        return
        
    # Handle the /search endpoint response
    if "results" in api_response:
        results = api_response.get("results", [])
        if not results:
            st.info("No matching items found in the catalog.")
            return
            
        st.markdown("<p style='color: #666; margin-bottom: 2rem;'>We found these items that closely match your inspiration.</p>", unsafe_allow_html=True)
        
        # More columns for smaller item boxes (4 items per row instead of 3 if wide)
        cols = st.columns(4)
        for idx, result in enumerate(results):
            col = cols[idx % 4]
            
            image_id = result.get("image_id", "")
            brand = result.get("brand", "Unknown").title()
            price = result.get("price_egp", "N/A")
            score = result.get("similarity_score", 0.0)
            product_url = result.get("product_url", "")
            
            with col:
                # Build sleek HTML item cards
                st.markdown(f"""
                <div style="background-color: #FFFFFF; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); overflow: hidden; margin-bottom: 1.5rem; transition: transform 0.2s ease, box-shadow 0.2s ease; border: 1px solid #F0F0F0;" 
                     onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.08)';"
                     onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.04)';">
                    <div style="padding: 1rem 1rem 0 1rem; position: relative;">
                """, unsafe_allow_html=True)
                
                # Render Image
                image_path = os.path.join(os.getcwd(), "data", "raw_images", f"{image_id}.jpg")
                if os.path.exists(image_path):
                    st.image(image_path, use_container_width=True)
                else:
                    st.warning("Image off-limit.")
                
                # Formatted metadata box underneath image
                st.markdown(f"""
                    </div>
                    <div style="padding: 1rem; text-align: left; border-top: 1px solid #FAFAFA;">
                        <span style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #888; font-weight: 600;">{brand}</span><br>
                        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                            <span style="color: #1A1A1A; font-weight: 700; font-size: 1.1rem; font-family: 'Inter', sans-serif;">{f"EGP {price:,.0f}" if isinstance(price, (int, float)) else price}</span>
                            <span style="font-size: 0.8rem; color: #2E8B57; background: #EAF4EE; padding: 2px 6px; border-radius: 4px;">{int(score * 100)}% Match</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Hover effect Shop Button
                if product_url:
                    st.markdown(f"""
                    <a href="{product_url}" target="_blank" style="text-decoration: none;">
                        <div style="background-color: #1A1A1A; color: #FFFFFF; text-align: center; padding: 0.6rem; border-radius: 4px; font-weight: 500; font-size: 0.9rem; transition: opacity 0.2s ease;">
                        🛍️ Shop Now
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
                st.write("") # spacer
        return

    # Handle the old /recommend endpoint if needed
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
