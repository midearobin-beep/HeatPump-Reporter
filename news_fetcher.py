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
from urllib.parse import urlparse

# ==========================================
# URL-Based Continent Detection
# ==========================================
# TLD -> continent mapping. Checked BEFORE falling back to query-config.
_TLD_TO_CONTINENT = {
    # Europe
    "uk": "Europe", "co.uk": "Europe", "gb": "Europe",
    "de": "Europe", "at": "Europe", "ch": "Europe",
    "fr": "Europe",
    "it": "Europe",
    "es": "Europe",
    "pt": "Europe",  # Portugal -> Europe, NOT South America
    "nl": "Europe", "be": "Europe",
    "pl": "Europe", "cz": "Europe", "sk": "Europe", "hu": "Europe",
    "ro": "Europe", "bg": "Europe",
    "se": "Europe", "no": "Europe", "dk": "Europe", "fi": "Europe",
    "gr": "Europe",
    "tr": "Europe",  # Türkiye is geographically on the border; we classify as Europe
    "eu": "Europe",
    # North America
    "us": "North America",
    "ca": "North America",
    "mx": "North America",
    # South America
    "br": "South America",
    "ar": "South America", "cl": "South America", "co": "South America",
    "pe": "South America", "ve": "South America",
    # Asia
    "ru": "Asia", "cn": "Asia", "jp": "Asia", "kr": "Asia",
    "in": "Asia", "vn": "Asia", "th": "Asia", "id": "Asia",
    "my": "Asia", "sg": "Asia", "ph": "Asia",
    "mn": "Asia",
    "ae": "Asia", "sa": "Asia", "il": "Asia",
    "kz": "Asia", "ua": "Asia",
    # Oceania
    "au": "Oceania", "nz": "Oceania",
    # Africa
    "za": "Africa", "ng": "Africa", "ke": "Africa", "eg": "Africa",
}

# Known US domains that use generic TLDs (.com / .net)
_US_DOMAINS = {
    "achrnews.com", "contractingbusiness.com", "hpac.com",
    "energystar.gov", "energy.gov", "epa.gov",
    "cbsnews.com", "foxnews.com", "fox43.com", "reuters.com",
    "bloomberg.com", "nytimes.com", "wsj.com", "washingtonpost.com",
    "energyvanguard.com", "greenbuildingadvisor.com",
    "hvacschool.com", "hvacinformed.com",
    "utilitydive.com", "greentech.media", "pv-magazine-usa.com",
    "canary.media", "e360.yale.edu", "sierraclub.org",
    "treehugger.com", "electrek.co", "cleantechnica.com",
}


# Known Portuguese (Portugal) media domains that use non-.pt TLDs
_PT_DOMAINS = {
    "canaln.tv", "rtp.pt", "sicnoticias.pt", "cmjornal.pt",
    "dn.pt", "jn.pt", "publico.pt", "observador.pt", "expresso.pt",
}

# Known Brazilian media domains that use non-.br TLDs  
_BR_DOMAINS = {
    "globo.com", "g1.globo.com", "terra.com.br", "r7.com",
}

def detect_continent_from_url(url: str, fallback: str = "Other") -> str:
    """Infer continent from article URL using TLD and known US domain lists."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().removeprefix("www.")

        # Check known US domains first (highest priority)
        if hostname in _US_DOMAINS or hostname.endswith(".gov") or hostname.endswith(".edu"):
            return "North America"

        # Check special-case national domains (non-obvious TLDs)
        if hostname in _PT_DOMAINS:
            return "Europe"
        if hostname in _BR_DOMAINS:
            return "South America"

        # Extract effective TLD (handle co.uk, com.br, etc.)
        parts = hostname.split(".")
        # Try 2-part suffix first (e.g. co.uk, com.br)
        if len(parts) >= 3:
            suffix2 = ".".join(parts[-2:])
            if suffix2 in _TLD_TO_CONTINENT:
                return _TLD_TO_CONTINENT[suffix2]
        # Then single TLD
        if len(parts) >= 2:
            tld = parts[-1]
            if tld in _TLD_TO_CONTINENT:
                return _TLD_TO_CONTINENT[tld]

        # .com / .net / .org / .io are global — use fallback from query config
        return fallback
    except Exception:
        return fallback

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
    三层图片提取链：
    1. og:image meta 标签
    2. twitter:image meta 标签
    3. 页面正文中最大的 <img>（宽/高 >= 200px 以过滤图标）
    任意一层成功即返回。
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        soup = BeautifulSoup(res.text, "html.parser")
        base_url = res.url  # actual URL after redirects

        def _is_valid(img_url: str) -> bool:
            if not img_url:
                return False
            if img_url.endswith(".svg"):
                return False
            if "googleusercontent.com" in img_url and "news.google.com" in url:
                return False
            # Must be absolute or resolvable
            return True

        def _abs(img_url: str) -> str:
            """Make URL absolute."""
            from urllib.parse import urljoin
            return urljoin(base_url, img_url) if img_url else ""

        # --- Layer 1: og:image ---
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og:
            candidate = og.get("content", "")
            if _is_valid(candidate):
                return _abs(candidate)

        # --- Layer 2: twitter:image ---
        tw = soup.find("meta", attrs={"name": "twitter:image"}) or \
             soup.find("meta", attrs={"property": "twitter:image"})
        if tw:
            candidate = tw.get("content", "")
            if _is_valid(candidate):
                return _abs(candidate)

        # --- Layer 3: largest <img> in article body (min 200px) ---
        best_img = None
        best_area = 0
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src", "")
            if not src or not _is_valid(src):
                continue
            # Skip tiny icons
            try:
                w = int(img_tag.get("width", 0))
                h = int(img_tag.get("height", 0))
            except (ValueError, TypeError):
                w, h = 0, 0
            # Prioritize images with explicit large dimensions
            if w >= 200 and h >= 100:
                area = w * h
                if area > best_area:
                    best_area = area
                    best_img = _abs(src)
            # Also accept images without dimensions if they look like article photos
            elif w == 0 and h == 0:
                lsrc = src.lower()
                if any(ext in lsrc for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    if best_img is None:  # only use as last resort
                        best_img = _abs(src)

        if best_img:
            return best_img

        return ""
    except Exception as e:
        print(f"Failed to extract image for {url}: {e}")
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
                        "continent": detect_continent_from_url(real_link, fallback=q.get("continent", "Other")),
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


# ==========================================
# 协会官网直抓 RSS 数据源
# ==========================================

# 各国热泵行业协会 RSS Feed 清单
ASSOCIATION_FEEDS = [
    # 欧洲 -------------------------------------------------------
    {
        "name": "EHPA (European Heat Pump Association)",
        "url":  "https://www.ehpa.org/feed/",
        "continent": "Europe",
        "lang": "English (EHPA)",
    },
    {
        "name": "ACR Journal (UK)",
        "url":  "https://www.acrjournal.uk/feed/",
        "continent": "Europe",
        "lang": "English (UK)",
    },
    {
        "name": "HVN Plus (UK)",
        "url":  "https://www.hvnplus.co.uk/rss/",
        "continent": "Europe",
        "lang": "English (UK)",
    },
    {
        "name": "Cooling Post (UK/Global)",
        "url":  "https://www.coolingpost.com/feed/",
        "continent": "Europe",
        "lang": "English (UK)",
    },
    {
        "name": "solarserver.de (Germany)",
        "url":  "https://www.solarserver.de/feed/",
        "continent": "Europe",
        "lang": "German",
    },
    {
        "name": "PV Magazine (International)",
        "url":  "https://www.pv-magazine.com/feed/",
        "continent": "Other",
        "lang": "English (Global)",
    },
    # 北美 -------------------------------------------------------
    {
        "name": "ACHR News (US)",
        "url":  "https://www.achrnews.com/rss/all",
        "continent": "North America",
        "lang": "English (US)",
    },
    {
        "name": "HPBA (Heat Pump & HVAC, US)",
        "url":  "https://www.hpba.org/feed/",
        "continent": "North America",
        "lang": "English (US)",
    },
    {
        "name": "Canary Media (US Clean Energy)",
        "url":  "https://www.canarymedia.com/feed",
        "continent": "North America",
        "lang": "English (US)",
    },
    # 亚太 -------------------------------------------------------
    {
        "name": "AIRAH (Australia HVAC)",
        "url":  "https://www.airah.org.au/rss/",
        "continent": "Oceania",
        "lang": "English (Australia)",
    },
]


def fetch_association_feeds(days_back: int = 3, max_per_feed: int = 5) -> List[Dict]:
    """
    从各国热泵行业协会 RSS 直接抓取最新新闻。
    比 Google News 更及时、更权威，适合官方数据和政策发布。
    """
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_back)
    history_cache = load_history()
    results = []

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; HeatPump-Reporter/1.0; +https://github.com/midearobin-beep/HeatPump-Reporter)"
    }

    for feed_cfg in ASSOCIATION_FEEDS:
        print(f"Fetching association feed: {feed_cfg['name']}...")
        try:
            resp = requests.get(feed_cfg["url"], headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"  → HTTP {resp.status_code}, skipping.")
                continue
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"  → Failed to fetch {feed_cfg['url']}: {e}")
            continue

        count = 0
        for entry in feed.entries:
            if count >= max_per_feed:
                break
            try:
                # Parse publish date
                pub_str = getattr(entry, "published", None) or getattr(entry, "updated", None)
                if pub_str:
                    from email.utils import parsedate_to_datetime
                    try:
                        pub_date = parsedate_to_datetime(pub_str)
                    except Exception:
                        import dateutil.parser
                        pub_date = dateutil.parser.parse(pub_str)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
                else:
                    pub_date = datetime.datetime.now(datetime.timezone.utc)

                if pub_date < cutoff_date:
                    continue

                link = entry.get("link", "")
                if not link or link in history_cache:
                    continue

                history_cache.append(link)

                # 提取图片
                og_image_url = extract_og_image(link)

                # 提取全文
                full_text = extract_full_text(link)
                fallback = getattr(entry, "summary", "")
                final_content = full_text if full_text else fallback

                results.append({
                    "title": entry.get("title", ""),
                    "link":  link,
                    "published": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": feed_cfg["name"],
                    "language": feed_cfg["lang"],
                    "continent": detect_continent_from_url(link, fallback=feed_cfg["continent"]),
                    "original_image_url": og_image_url,
                    "summary": final_content,
                })
                count += 1
            except Exception as e:
                print(f"  → Error parsing entry: {e}")

    save_history(history_cache)
    print(f"\n协会官网: 共抓取 {len(results)} 篇新文章。")
    return results
