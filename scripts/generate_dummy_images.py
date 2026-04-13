import os
import json
from PIL import Image

# 1. Create the target directory for the images
os.makedirs("data/images", exist_ok=True)

# 2. Barawy's exact mock dataset
mock_data = [
  {"id": "001", "name": "Blue Basic T-Shirt", "color": "blue"},
  {"id": "002", "name": "Black Basic T-Shirt", "color": "black"},
  {"id": "003", "name": "White Basic T-Shirt", "color": "white"},
  {"id": "004", "name": "Black Hoodie", "color": "black"},
  {"id": "005", "name": "White Hoodie", "color": "white"},
  {"id": "006", "name": "Black Hoodie", "color": "black"},
  {"id": "007", "name": "Gray Hoodie", "color": "gray"},
  {"id": "008", "name": "Black Jacket", "color": "black"},
  {"id": "009", "name": "Black Jacket", "color": "black"},
  {"id": "010", "name": "Black Crewneck", "color": "black"},
  {"id": "011", "name": "White Crewneck", "color": "white"},
  {"id": "012", "name": "Gray Sweatpants", "color": "gray"},
  {"id": "013", "name": "Black Sweatpants", "color": "black"},
  {"id": "014", "name": "Gray Sweatpants", "color": "gray"},
  {"id": "015", "name": "Black Sweatpants", "color": "black"},
  {"id": "016", "name": "Blue Jeans", "color": "blue"},
  {"id": "017", "name": "Blue Jeans", "color": "blue"},
  {"id": "018", "name": "Nike Air Force 1", "color": "white"},
  {"id": "019", "name": "Adidas Ultraboost", "color": "black"}
]

# 3. RGB Color Mapping
color_map = {
    "blue": (0, 0, 255),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128)
}

# 4. Generate the 224x224 images
print("Generating dummy images for testing...")
for item in mock_data:
    # Look up the color, default to gray if missing
    rgb = color_map.get(item["color"].lower(), (128, 128, 128))
    
    # Create the image and save it using the item's ID
    img = Image.new("RGB", (224, 224), rgb)
    img_path = f"data/raw_images/{item['id']}.jpg"
    img.save(img_path)
    
    print(f"✅ Saved {img_path} ({item['name']})")

print("\nSuccess! All 19 test images are ready.")