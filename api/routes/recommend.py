import uuid
import os
import io
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from PIL import Image

# ─── FUTURE DEVELOPMENT: OpenAI RAG Pipeline ───
# Uncomment these when OpenAI credits are restored
# from api.services.recommendation_service import RecommendationService
# recommendation_service = RecommendationService()

# ─── LOCAL AI PIPELINE ───
from ai_engine.embeddings.encoder import get_encoder
from ai_engine.embeddings.vector_store import FAISSVectorStore

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class RecommendedItem(BaseModel):
    id: str
    category: str
    image_url: str
    price: Optional[Any] = "N/A"
    brand: Optional[str] = "ChicFinder Local"

class RecommendationResponse(BaseModel):
    query_item: Dict[str, Any]
    recommendations: List[RecommendedItem]

# Force CPU mode to avoid the VRAM crash during local testing
os.environ["CUDA_VISIBLE_DEVICES"] = ""

router = APIRouter()

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Initialize local vector store globally
vector_store = FAISSVectorStore.get_instance()

def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/recommend")
async def get_recommendations(file: UploadFile = File(...)):
    suffix = Path(file.filename or "image.png").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Images only.")

    raw_bytes = await file.read()
    
    # ─── 1. BULLETPROOF IMAGE SANITIZATION ───
    try:
        # Force the image open to verify it
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        _ensure_uploads_dir()
        saved_filename = f"{uuid.uuid4()}_clean.png"
        save_path = UPLOADS_DIR / saved_filename
        img.save(save_path, format="PNG")
        
        clean_bytes = save_path.read_bytes()
        query_url = f"/uploads/{saved_filename}"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Corrupted image format. Error: {e}")
        
    # ─────────────────────────────────────────────
    # ─── FUTURE DEVELOPMENT: OPENAI PIPELINE ───
    # To enable OpenAI later, change the ''' block quotes to run the code
    '''
    try:
        print("🤖 Attempting Full OpenAI RAG Pipeline...")
        recommendations = recommendation_service.process_recommendation(clean_bytes)

        return {
            "success": True,
            "query_url": query_url,
            "engine_used": "OpenAI_Full_RAG",
            "recommendations": recommendations,
        }
    except Exception as e:
        print(f"⚠️ OpenAI Pipeline Failed ({e}). Instantly falling back to Local Model!")
    '''

    # ─── 2. LOCAL FASHIONCLIP + FAISS SEARCH ───
    try:
        print("🚀 Running Local FashionCLIP Pipeline...")
        encoder = get_encoder()
        
        # 1. We encode the PIL image straight into a normalized vector
        raw_vector = encoder._encode(img)
        query_vector = encoder._normalize(raw_vector)
        
        # 2. 🔥 THE FIX: Use search_by_vector! (This expects a numpy array)
        # This returns a clean list of dictionaries natively.
        results = vector_store.search_by_vector(query_vector, top_k=5)
        
        # 3. Format the results
        fallback_items = []
        for meta in results:
            # Get the raw path: "data\images\018.jpg"
            raw_path = meta.get("image_url", "")
            
            # Normalize slashes: "data/images/018.jpg"
            normalized_path = raw_path.replace("\\", "/")
            
            # Map it to your mounted endpoint. 
            # If your dataset mount serves the "data" folder, make it "/images/018.jpg"
            clean_web_url = "/" + normalized_path.replace("data/", "")
            
            fallback_items.append(RecommendedItem(
                id=str(meta.get("id")),
                category=meta.get("category", "Local Match"),
                image_url=meta.get("image_url", ""),
                price=meta.get("price", "N/A"),
                brand=meta.get("brand", "ChicFinder Local")
            ))
        
        # Create a mock "Query Item" so the UI doesn't break
        fallback_recommendation = RecommendationResponse(
            query_item={"type": "Full Outfit", "description": "Local Visual Search Match"},
            recommendations=fallback_items
        )
        
        return {
            "success": True,
            "query_url": query_url,
            "engine_used": "Local_FashionCLIP_FAISS",
            "recommendations": [fallback_recommendation]
        }
        
    except Exception as local_e:
        print(f"CRITICAL LOCAL ERROR: {local_e}")
        raise HTTPException(status_code=500, detail=f"Local Engine Crash: {local_e}")