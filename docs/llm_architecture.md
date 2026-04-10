# ChicFinder AI & LLM Architecture

ChicFinder utilizes a sophisticated multimodal Retrieval-Augmented Generation (RAG) pipeline based on the **OutfitAI** architecture. This document outlines the core LLM and AI components implemented in the `ai_engine` module.

## Architecture Pipeline

The recommendation pipeline converts a source image containing an outfit into a list of purchasable clothing items via the following steps:

1.  **LLM Outfit Parsing (`OutfitParser`)**: Uses **GPT-4o Vision** to analyze the input image and decompose it into distinct items (e.g., top, bottom, shoes), extracting rich metadata (type, color, style, gender, material, fit).
2.  **Query Encoding (`FashionCLIPEncoder`)**: Converts the image into a dense 512-dimensional semantic embedding using the **FashionCLIP** model (`patrickjohncyh/fashion-clip` via HuggingFace Transformers), with L2 normalization applied for cosine similarity compatibility.
4.  **Vector Retrieval (`FAISSVectorStore` & `Retriever`)**: Executes a fast Approximate Nearest Neighbor (ANN) search over a **FAISS** index (`IndexFlatIP`) using the 512-d embedding. The index intrinsically calculates cosine similarity since vectors are L2 normalized.
5.  **Vision Reranking (`VisionReranker`)**: Passes the query outfit image and the top-$K$ candidate product images back to **GPT-4o Vision** for a fine-grained, visual-similarity-based reranking.

---

## Core Components

### 1. Large Language Models (LLM) Integration

The `ai_engine/llm` module handles interactions with OpenAI's GPT-4o.

*   **`OutfitParser` (`llm/outfit_parser.py`)** 
    Takes a PIL Image and sends it to GPT-4o with a strict system prompt (defined in `prompt_builder.py`). Returns a structured JSON array of clothing items (type, color, style, fit, etc.).
*   **`VisionReranker` (`llm/reranker.py`)**
    Takes a query image and multiple candidate images. Sends them natively in a single API call to GPT-4o. The model returns a JSON array of indices ranking the candidates from most to least visually similar. Uses batched calls internally if candidates exceed the maximum per-call limit (10).
*   **`prompt_builder.py`**
    Centralizes all complex prompt templates for easy tuning.

### 2. Embeddings & Vector Database

The `ai_engine/embeddings` module handles offline indexing and online semantic encoding.

*   **`FashionCLIPEncoder` (`embeddings/encoder.py`)** 
    Wraps the `patrickjohncyh/fashion-clip` model (CLIP ViT-B/32, fine-tuned on ~700k Farfetch fashion images). Decodes raw image bytes to a PIL RGB image, runs it through the CLIP vision encoder, and returns a 512-dimensional L2-normalized embedding. Pre-trained on fashion-specific data, making it robust to backgrounds without requiring explicit background removal.
*   **`FAISSVectorStore` (`embeddings/vector_store.py`)**
    A fully offline FAISS index (`faiss-cpu`, `IndexFlatIP`). Drops the heavy Marqo dependency in favor of a self-contained local vector database. Stores the index binary and parallel metadata JSON to disk. Exposes both `search(image_bytes)` (encode + search) and `search_by_vector(query_vector)` (pre-computed embedding search) methods.
*   **`FAISSIndexBuilder` (`embeddings/database_builder.py`)**
    Offline indexing utility. Scans a directory of fashion photos, encodes them via `FashionCLIPEncoder`, and saves the resulting 512-d vectors into the `FAISSVectorStore`. 

### 3. Orchestration

*   **`RAGPipeline` (`rag/pipeline.py`)**
    Orchestrator class. Lazily instantiates all heavy DL and API components to optimize startup times (beneficial for FastAPI). Chains the segmenter, parser, encoder, retriever, and reranker together, exposing a clean `.run(image)` method that yields typed `Recommendation` response objects.

---

## Developer Scripts

### Building the Database Offline
Before the retrieval pipeline can work, you must populate the FAISS database with candidate product images. Use the included script:

```bash
# Build from a local directory of images
python -m scripts.build_database --images ./data/raw_images --out ./data/embeddings.index
```

### Smoke Testing the Pipeline
Validate the full AI pipeline end-to-end without needing to start the web server:

```bash
# Level 1: Fast test. Validates imports, PyTorch dependencies, and lazy initializations
python -m scripts.test_pipeline --level 1

# Level 2: Runs the pipeline with real vector retrieval, but skips GPT-4o reranking
python -m scripts.test_pipeline --level 2 --image test_outfit.jpg

# Level 3: Full execution including expensive GPT-4o vision reranking
python -m scripts.test_pipeline --level 3 --image test_outfit.jpg
```

---

## Dependencies Updates

The underlying requirements have been updated to support this architecture:
- Added `openai>=1.0.0` for the modern Pydantic-based client.
- Replaced `marqo` with `faiss-cpu` for lightweight local inference.
- Added `requests` for fetching remote candidate images during retrieval and processing.
