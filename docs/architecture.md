# ChicFinder Architecture

ChicFinder follows the **OutfitAI** research paper architecture for intelligent outfit recommendations.

## RAG Pipeline Flow

1. **User Upload**: Photo uploaded via Streamlit.
2. **Background Removal**: `FashionSegmenter` (ViT-B / SETR) removes noise and isolates the user.
3. **LLM Outfit Parsing**: `OutfitParser` (GPT-4o Vision) identifies individual items (e.g., "blue denim jacket", "white cotton t-shirt").
4. **Item Retrieval**:
    - **Encoding**: `FashionEncoder` (VGG-16) generates 256-dim embeddings.
    - **KNN Search**: `VectorStore` (FAISS) finds the top 25 similar items in the database.
5. **Vision Reranking**: `VisionReranker` (GPT-4o Vision) performs fine-grained comparison between the query image and candidates.
6. **Results**: Recommendations displayed in the Streamlit UI.

## Component Overview

- `ai-engine/`: Core algorithmic logic.
- `api/`: FastAPI service providing the recommendation endpoint.
- `frontend/`: Interactive Streamlit dashboard.
- `shared/`: Common schemas and utilities used across modules.
