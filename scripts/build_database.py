import argparse
from ai_engine.embeddings.database_builder import DatabaseBuilder

def main():
    parser = argparse.ArgumentParser(description="Build ChicFinder FAISS Index")
    parser.add_argument("--images", type=str, required=True, help="Path to images directory")
    parser.add_argument("--out", type=str, required=True, help="Path to output FAISS index")
    
    args = parser.parse_args()
    
    builder = DatabaseBuilder(images_dir=args.images, out_path=args.out)
    print(f"Building database from {args.images} to {args.out}...")
    builder.build()
    print("Database build complete.")

if __name__ == "__main__":
    main()
