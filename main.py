import os
import datetime
from news_fetcher import fetch_multilingual_news
from ai_processor import refine_news_with_ai
from image_fetcher import fetch_image, download_original_image
from ppt_generator import create_news_ppt

def main():
    print("1. 开始从欧洲及全球抓取多语种行业新闻...")
    # Fetch multi-lingual heat pump related news in the last 7 days
    raw_news = fetch_multilingual_news(days_back=7, max_results_per_lang=4)
    print(f"   => 成功抓取到 {len(raw_news)} 篇原始文章。")
    
    print("\n2. 使用 DeepSeek AI 深度翻译并提炼核心...")
    refined_news = refine_news_with_ai(raw_news)
    print(f"   => AI 处理完成，保留了 {len(refined_news)} 篇高价值见解。")
    
    print("\n3. 正在自动匹配图片物料...")
    os.makedirs("assets", exist_ok=True)
    for idx, item in enumerate(refined_news):
        print(f"   - 正在为 '{item.get('headline')}' 获取配图...")
        img_path = f"assets/news_img_{idx}.png"
        
        # Priority 1: Original Image
        og_url = item.get("original_image_url")
        success = False
        if og_url:
            print(f"     -> 发现原始新闻头图，尝试下载...")
            success = download_original_image(og_url, img_path)
            
        # Priority 2: AI Generated Image
        if not success:
            print(f"     -> 使用 MiniMax 开始 AI 作图...")
            analysis_data = item.get("analysis", {})
            fetch_image(analysis_data, img_path)
            
        item['image_path'] = img_path

    print("\n4. 正在合成排版 PPT...")
    # Calculate the ISO calendar week format (e.g. 2026CW15)
    now = datetime.datetime.now()
    year, week, _ = now.isocalendar()
    output_filename = f"{year}CW{week:02d}_HeatPump_Weekly_Report.pptx"
    
    create_news_ppt(refined_news, output_filename)
    
    print(f"\n全部流程执行完毕！最终报告位于: {os.path.abspath(output_filename)}")

if __name__ == "__main__":
    main()
