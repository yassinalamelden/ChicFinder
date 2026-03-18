from PIL import Image
from ai_engine.rag.pipeline import RAGPipeline

def main():
    print("Initializing RAG Pipeline...")
    pipeline = RAGPipeline()
    
    print("Creating mock image for testing...")
    mock_image = Image.new('RGB', (512, 512), color='red')
    
    print("Running pipeline test...")
    try:
        results = pipeline.run(mock_image)
        print("Pipeline test executed successfully.")
        print(f"Results: {results}")
    except NotImplementedError as e:
        print(f"Pipeline executed up to stub: {e}")
    except Exception as e:
        print(f"Pipeline test failed: {e}")

if __name__ == "__main__":
    main()
