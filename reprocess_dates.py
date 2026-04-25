import os
import json
import datetime
from news_fetcher import extract_full_text, extract_og_image
from ai_processor import refine_news_with_ai
from image_fetcher import fetch_image, download_original_image
from ppt_generator import create_news_ppt
import trafilatura

def get_article_info(url):
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    
    # Try to extract date
    metadata = trafilatura.extract_metadata(downloaded)
    date_str = metadata.date if metadata and metadata.date else ""
    title = metadata.title if metadata and metadata.title else "Unknown Title"
    
    full_text = extract_full_text(url)
    og_img = extract_og_image(url)
    
    return {
        'url': url,
        'title': title,
        'date': date_str,
        'full_text': full_text,
        'og_img': og_img
    }

def run_reprocess():
    with open('history.json', 'r') as f:
        urls = json.load(f)

    # We take the last 50 urls to find recent ones
    recent_urls = urls[-60:]
    
    all_data = []
    print(f"Checking {len(recent_urls)} URLs for target dates...")
    
    for url in recent_urls:
        info = get_article_info(url)
        if info and info['date']:
            # Handle formats like 2026-04-23
            if any(d in info['date'] for d in ['2026-04-21', '2026-04-22', '2026-04-23']):
                all_data.append(info)
                print(f"  [FOUND] {info['date']}: {info['title']}")
    
    # Group by date
    dates = ['2026-04-21', '2026-04-22', '2026-04-23']
    for target_date in dates:
        output_ppt = f"{target_date}_HeatPump_REGENERATED.pptx"
        if os.path.exists(output_ppt):
            print(f"\nSkipping {target_date} as {output_ppt} already exists.")
            continue

        day_items = [d for d in all_data if target_date in d['date']]
        if not day_items:
            print(f"\nNo items found for {target_date}, skipping.")
            continue
            
        print(f"\n--- Reprocessing {target_date} ({len(day_items)} items) ---")
        
        news_to_ai = []
        for item in day_items:
            news_to_ai.append({
                'title': item['title'],
                'link': item['url'],
                'published': item['date'],
                'source': 'Archive',
                'summary': item['full_text'],
                'original_image_url': item['og_img']
            })
            
        refined = refine_news_with_ai(news_to_ai)
        
        # Handle images
        os.makedirs('assets', exist_ok=True)
        for i, item in enumerate(refined):
            img_filename = f"assets/regen_{target_date}_{i}.png"
            if not download_original_image(item.get('original_image_url'), img_filename):
                fetch_image(item.get('analysis', {}), img_filename)
            item['image_path'] = img_filename
            
        output_ppt = f"{target_date}_HeatPump_REGENERATED.pptx"
        create_news_ppt(refined, output_ppt)
        print(f"Success! Generated {output_ppt}")

if __name__ == "__main__":
    run_reprocess()
