import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

def fetch_image(query: str, download_path: str) -> str:
    """
    Generate an image using MiniMax API,
    and return the path to the downloaded image.
    If no API key is set, returns a placeholder image path.
    """
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key or api_key == "your_minimax_api_key_here":
        print("Warning: MINIMAX_API_KEY not set. Generating a placeholder gradient.")
        return _create_placeholder_image(download_path)

    url = "https://api.minimaxi.com/v1/image_generation"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # English prompts work best for image generation
    prompt = f"Professional clean photo of {query}, modern commercial HVAC or heat pump system, sustainable green energy concept, highly detailed, realistic, 4k"

    payload = {
        "model": "image-01",
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "response_format": "base64",
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if "data" in data and "image_base64" in data["data"] and len(data["data"]["image_base64"]) > 0:
            b64_image = data["data"]["image_base64"][0]
            img_data = base64.b64decode(b64_image)
            
            with open(download_path, 'wb') as handler:
                handler.write(img_data)
            return download_path
        else:
            print("MiniMax API returned an unexpected response structure:", data)
            return _create_placeholder_image(download_path)
            
    except Exception as e:
        print(f"Error generating image from MiniMax API: {e}")
        return _create_placeholder_image(download_path)

def _create_placeholder_image(path: str) -> str:
    """
    Create a simple blank placeholder if the API fails or is not configured.
    """
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (800, 600), color=(44, 62, 80))
        d = ImageDraw.Draw(img)
        d.text((300, 300), "No Image Available\n(API missing/failed)", fill=(255, 255, 255))
        img.save(path)
        return path
    except ImportError:
        tiny_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        with open(path, 'wb') as f:
            f.write(tiny_png)
        return path

def download_original_image(url: str, download_path: str) -> bool:
    """
    Attempts to download the original image from the provided URL.
    Returns True if successful, False otherwise.
    """
    if not url:
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        # Save raw content first
        raw_path = download_path + ".raw"
        with open(raw_path, 'wb') as f:
            f.write(res.content)
            
        # Inspect and convert to PNG/RGB to avoid WebP/python-pptx issues
        try:
            from PIL import Image
            with Image.open(raw_path) as img:
                img = img.convert("RGB")
                img.save(download_path, "PNG")
            import os
            os.remove(raw_path)
            return True
        except Exception as e:
            print(f"PIL conversion failed for {url}: {e}")
            import os
            os.remove(raw_path)
            return False
            
    except Exception as e:
        print(f"Failed to download original image {url}: {e}")
        return False

if __name__ == "__main__":
    p = fetch_image("heat pump", "test_image.png")
    print(f"Image saved to {p}")
