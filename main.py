import os
import datetime
from news_fetcher import fetch_multilingual_news, fetch_association_feeds
from ai_processor import refine_news_with_ai
from image_fetcher import download_original_image
from ppt_generator import create_news_ppt

def main():
    print("1. 开始从欧洲及全球抓取多语种行业新闻...")
    # Google News 关键词搜索（过去2天）
    raw_news = fetch_multilingual_news(days_back=2, max_results_per_lang=4)
    print(f"   => Google News: {len(raw_news)} 篇原始文章。")

    # 协会官网直抓（过去3天，确保不遗漏）
    print("\n1b. 抓取行业协会官网直连源（EHPA/ACHR/CoolingPost 等）...")
    assoc_news = fetch_association_feeds(days_back=3, max_per_feed=5)
    print(f"   => 协会源: {len(assoc_news)} 篇新文章。")

    # 合并并按 URL 去重
    seen_links = {item["link"] for item in raw_news}
    for item in assoc_news:
        if item["link"] not in seen_links:
            raw_news.append(item)
            seen_links.add(item["link"])
    print(f"   => 合并去重后共 {len(raw_news)} 篇，进入 AI 处理。")
    
    print("\n2. 使用 DeepSeek AI 深度翻译并提炼核心...")
    refined_news = refine_news_with_ai(raw_news)
    print(f"   => AI 处理完成，保留了 {len(refined_news)} 篇高价值见解。")
    
    print("\n3. 正在匹配新闻配图...")
    os.makedirs("assets", exist_ok=True)
    for idx, item in enumerate(refined_news):
        img_path = f"assets/news_img_{idx}.png"
        og_url = item.get("original_image_url")
        if og_url and download_original_image(og_url, img_path):
            item["image_path"] = img_path
        # 无图则不设 image_path，PPT 生成器会跳过图片位置

    print("\n4. 正在合成排版 PPT...")
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    output_filename = f"{date_str}_HeatPump_Daily_Briefing.pptx"
    
    create_news_ppt(refined_news, output_filename)
    
    print(f"\n全部流程执行完毕！最终报告位于: {os.path.abspath(output_filename)}")

if __name__ == "__main__":
    main()
