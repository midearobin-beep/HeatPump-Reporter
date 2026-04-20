import os
from image_fetcher import fetch_image

sample_data = {
    "category": "市场趋势",
    "country": "UK",
    "theme": "sales growth",
    "target": "residential",
    "tone": "optimistic"
}

print("Running image generator...")
fetch_image(sample_data, "test_uk_market.png")
print("Done!")
