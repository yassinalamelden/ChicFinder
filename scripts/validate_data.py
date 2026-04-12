import json
import os

def validate():
    json_path = "data/mock_fashion_data.json" # Or whatever Barawy names it
    img_dir = "data/images"
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    for item in data:
        img_name = f"{item['id'].zfill(3)}.jpg" # Adjust based on his naming convention
        full_path = os.path.join(img_dir, img_name)
        if not os.path.exists(full_path):
            print(f"❌ Missing Image: {img_name} for ID {item['id']}")
    print("Validation Complete!")

if __name__ == "__main__":
    validate()