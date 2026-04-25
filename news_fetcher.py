import urllib.parse
import feedparser
import datetime
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import googlenewsdecoder

import yaml
import os
import json
import trafilatura

def load_history():
    cache_path = os.path.join(os.path.dirname(__file__), "history.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_history(history_list):
    cache_path = os.path.join(os.path.dirname(__file__), "history.json")
    # Limiting history size to last 1000 items to avoid giant files over time
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(history_list[-1000:], f, ensure_ascii=False, indent=2)

def load_queries():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get("queries", [])
    return []

QUERIES = load_queries()

def extract_og_image(url: str) -> str:
    """
    Follows a news link and attempts to extract the `<meta property="og:image">` URL.
    Returns empty string if failed.
    """
    try:
        # First, strictly decode the obscure Google News URL
        real_url = url
        try:
            res = googlenewsdecoder.new_decoderv1(url)
            if res and res.get('status'):
                real_url = res.get('decoded_url')
        except Exception:
            pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(real_url, headers=headers, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(res.text, "html.parser")
        og_img = soup.find("meta", property="og:image")
        
        if og_img and og_img.get("content"):
            content_url = og_img["content"]
            # Filter out blank placeholders or bad domains
            if "googleusercontent.com" in content_url and "news.google.com" in real_url:
                return ""
            if content_url.endswith(".svg"):
                return ""
            return content_url
        return ""
    except Exception as e:
        print(f"Failed to extract og:image for {url}: {e}")
        return ""

def extract_full_text(url: str) -> str:
    """
    Downloads and extracts the entire reading text from a URL using Trafilatura.
    Returns empty string if failed.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                return text
        return ""
    except Exception as e:
        print(f"Trafilatura failed to extract text for {url}: {e}")
        return ""

def fetch_multilingual_news(days_back: int = 7, max_results_per_lang: int = 5) -> List[Dict]:
    """
    Fetch news from Google News RSS across multiple languages.
    """
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_back)
    results = []
    
    # Load past run history to prevent duplicate reports
    history_cache = load_history()

    for q in QUERIES:
        time_query = f"{q['query']} when:{days_back}d"
        encoded_query = urllib.parse.quote_plus(time_query)
        url = f"https://news.google.com/rss/search?q={encoded_query}{q['params']}"
        
        print(f"Fetching {q['lang']} news...")
        feed = feedparser.parse(url)
        
        count = 0
        for entry in feed.entries:
            if count >= max_results_per_lang:
                break
                
            try:
                from email.utils import parsedate_to_datetime
                pub_date = parsedate_to_datetime(entry.published)
                
                if pub_date >= cutoff_date:
                    # Resolve real url for the final feed record 
                    real_link = entry.link
                    try:
                        dec = googlenewsdecoder.new_decoderv1(entry.link)
                        if dec and dec.get('status'):
                            real_link = dec.get('decoded_url')
                    except Exception:
                        pass
                        
                    # Check against deduplication history
                    if real_link in history_cache:
                        print(f"     -> 发现近期处理过的新闻，跳过归档: {entry.title}")
                        continue
                        
                    history_cache.append(real_link)
                        
                    # Try extracting original image from real link
                    og_image_url = extract_og_image(real_link)
                    
                    # Fetch FULL TEXT to feed the AI and prevent hallucination
                    full_text = extract_full_text(real_link)
                    fallback_summary = getattr(entry, "summary", "")
                    final_content = full_text if full_text else fallback_summary
                    
                    results.append({
                        "title": entry.title,
                        "link": real_link,
                        "published": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "source": entry.source.title if hasattr(entry, 'source') else "Google News",
                        "language": q["lang"],
                        "continent": q.get("continent", "Other"),
                        "original_image_url": og_image_url,
                        "summary": final_content
                    })
                    count += 1
            except Exception as e:
                print(f"Error parsing entry {entry.title}: {e}")
                
    # Save the updated history for the next run
    save_history(history_cache)
                
    return results

if __name__ == "__main__":
    news = fetch_multilingual_news(days_back=7, max_results_per_lang=2)
    for n in news:
        print(f"[{n['published']}] ({n['language']}) {n['source']}: {n['title']}\nOriginal Image: {n['original_image_url']}\n")
