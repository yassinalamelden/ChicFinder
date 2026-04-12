import os
import io
import json
import base64
import logging

logger = logging.getLogger(__name__)

def extract_features(image_bytes: bytes) -> dict:
    default_response = {
        "category": None,
        "color": None,
        "style": None,
        "fabric": None,
        "gender": None
    }
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment.")
        return default_response
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        base64_img = base64.b64encode(image_bytes).decode('utf-8')
        
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={ "type": "json_object" },
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Analyze this clothing item and return a JSON object exactly with keys: 'category', 'color', 'style', 'fabric', 'gender'. If a feature is unknown, set it to null. Use strictly lowercase strings."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=200
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        return {
            "category": data.get("category", "").lower() if data.get("category") else None,
            "color": data.get("color", "").lower() if data.get("color") else None,
            "style": data.get("style", "").lower() if data.get("style") else None,
            "fabric": data.get("fabric", "").lower() if data.get("fabric") else None,
            "gender": data.get("gender", "").lower() if data.get("gender") else None,
        }

    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        return default_response
