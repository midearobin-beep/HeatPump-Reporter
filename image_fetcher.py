import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

def generate_news_prompt(analysis: dict) -> str:
    category = analysis.get("category", "")
    country = analysis.get("country", "")
    theme = analysis.get("theme", "")
    target = analysis.get("target", "")
    tone = analysis.get("tone", "")

    base_templates = {
        "政策法规": "Professional editorial news photo, European government architecture, clean energy transition context, realistic photography, natural daylight, Reuters style, serious tone",
        "企业新闻": "Corporate news photo of modern HVAC headquarters or modern office building facade, professional business aesthetic, corporate PR photography style",
        "产品发布": "Premium product launch photo of a modern air-to-water heat pump installed prominently, cinematic lighting, realistic materials, clean composition, industry magazine style",
        "技术突破": "High-tech industrial photography of HVAC engineering, heat pump internals or laboratory testing, engineering realism, detailed, science magazine style",
        "市场趋势": "Editorial photo showing suburban homes adopting heat pumps, clear market growth implication, realistic street scene, financial news style, Bloomberg aesthetic",
        "安装案例": "Documentary realism photo of an installed heat pump outdoor unit, integrated with building exterior, professional installer context, realistic daylight",
        "能源价格": "Editorial photo contrasting natural gas elements with electrical green energy, city context, subtle data or chart implication, Financial Times style",
        "环保议题": "Green technology photography, earth and residential elements, clear sky, highly optimistic clean energy transition, documentary style"
    }

    country_styles = {
        "Germany": "German suburban houses",
        "UK": "British traditional brick homes",
        "France": "French elegant townhouses",
        "Netherlands": "Dutch row houses",
        "Nordic": "Scandinavian wooden painted homes",
        "Italy": "Italian terracotta roof houses",
        "Spain": "Spanish sunshine Mediterranean style homes"
    }

    prompt_base = base_templates.get(category, "Professional clean photo of modern commercial HVAC or heat pump system, sustainable green energy concept, highly detailed, realistic, 4k")
    country_style = ""
    for k, v in country_styles.items():
        if k.lower() in country.lower():
            country_style = v
            break
    
    components = [prompt_base]
    if target == "residential" and country_style:
        components.append(f"Context: {country_style} with realistic heat pump outdoor unit subtly visible.")
    elif target in ["commercial", "industrial"]:
        components.append("Context: Large scale commercial rooftop heat pump installation or industrial facility.")
    else:
        components.append("Realistic installed residential heat pump unit beside brick house.")

    if theme:
        components.append(f"Subject Theme: {theme}, {tone} atmosphere.")

    components.append("Industry elements: air-to-water heat pump, monobloc, low carbon heating, smart energy.")
    components.append("(Negative Prompt: cartoon, CGI, futuristic sci-fi, distorted unit, extra fans, unreadable text, duplicated houses, weird pipes, floating objects)")

    return " | ".join(components)


def fetch_image(analysis_data: dict, download_path: str) -> str:
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
    
    prompt = generate_news_prompt(analysis_data)
    print(f"     [Vision System Prompt]: {prompt}")

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
