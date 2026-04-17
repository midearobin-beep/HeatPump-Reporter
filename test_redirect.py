import requests
from bs4 import BeautifulSoup
import feedparser

feed = feedparser.parse("https://news.google.com/rss/search?q=heat+pump&hl=en-US&gl=US&ceid=US:en")
link = feed.entries[0].link

print("RSS Link:", link)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}
res = requests.get(link, headers=headers, allow_redirects=True, timeout=10)
print("Resolved URL:", res.url)
soup = BeautifulSoup(res.text, "html.parser")
og = soup.find("meta", property="og:image")
print("OG Image:", og["content"] if og else None)
print("Title:", soup.title.text if soup.title else None)
