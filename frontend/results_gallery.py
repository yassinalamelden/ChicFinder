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
        
    results = api_response.get("results", [])
    
    if not results:
        st.info("No matching outfits found.")
        return
        
    processing_time = api_response.get("processing_time_ms")
    if processing_time is not None:
        st.caption(f"Processed in {processing_time} ms")
        
    cols = st.columns(3)
    for i, item in enumerate(results):
        # We ensure no KeyError by only using dict.get()
        if not isinstance(item, dict):
            continue
            
        with cols[i % 3]:
            # Container for styling
            with st.container():
                # 1. Display Image
                image_id = item.get("image_id")
                if image_id:
                    image_path = f"data/raw_images/{image_id}.jpg"
                    if os.path.exists(image_path):
                        st.image(image_path, use_container_width=True)
                    else:
                        try:
                            # Fallback in case os checks act up in different OS or Streamlit loads it differently
                            st.image(image_path, use_container_width=True)
                        except Exception:
                            st.write(f"📷 *Image locally unavailable ({image_id})*")
                
                # 2. Similarity score
                score = item.get("similarity_score")
                if score is not None:
                    st.metric("Similarity", f"{score:.0%}")
                    
                # 3. Brand
                brand = item.get("brand")
                if brand:
                    st.write(f"**Brand:** {brand}")
                    
                # 4. Price in EGP
                price = item.get("price_egp")
                if price is not None:
                    st.write(f"**Price:** {price} EGP")
                    
                # 5. Store Location
                location = item.get("store_location")
                if location:
                    st.write(f"**Location:** {location}")
                    
                # 6. Availability in Egypt
                available = item.get("availability_egypt")
                if available is not None:
                    status = "✅ Available" if available else "❌ Out of Stock"
                    st.write(f"**Egypt Availability:** {status}")
                    
                # 7. Product URL
                url = item.get("product_url")
                if url:
                    st.markdown(f"[View Product]({url})")
                    
                st.divider()
