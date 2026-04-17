import os
import json
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def refine_news_with_ai(news_items: List[Dict]) -> List[Dict]:
    """
    Takes a list of fetched news dictionaries, translates and summarizes them
    into a structured JSON array format.
    """
    if not news_items:
        return []

    # Get API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("Warning: DEEPSEEK_API_KEY not set. Using dummy data.")
        return [
            {
                "headline": "示例新闻：德国增加热泵补贴",
                "summary": "德国政府宣布将为安装高效热泵的家庭提供高达70%的安装补贴，以加速淘汰化石燃料供暖系统。",
                "tags": ["补贴", "欧洲市场"],
                "source": "Dummy Source",
                "date": "2026-04-09"
            }
        ]

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    # Format input for LLM
    input_text = "Here are the latest news items:\n\n"
    for idx, item in enumerate(news_items):
        input_text += f"{idx+1}. Title: {item['title']}\nLink: {item['link']}\nSource: {item['source']}\nLanguage: {item.get('language','')}\nDate: {item.get('published','')}\nOriginal Image: {item.get('original_image_url','')}\n\n"

    system_prompt = """
    你是一个专业的热泵(Heat Pump)与HVAC行业、新能源政策分析师。
    你将收到一份近期全球行业新闻列表（包含多语种如英语、德语、法语）。
    任务：
    1. 滤除毫不相关的新闻或质量极低的PR稿。合并报道同一事件的新闻。
    2. 将剩余的、最重要的新闻（最多保留 7 条）深度翻译并解读为中文。
    3. 必须以严格的 JSON 格式输出，返回一个包含 "news" 键的字典，"news" 的值是一个对象数组。
    
    输出的 JSON 格式范例：
    {
      "news": [
        {
          "headline": "中文新闻大标题",
          "summary": "一段约100-150字左右的详尽背景概述，需要带有深度和专业性，阐明行业背景、政策影响或技术突破情况。",
          "bullet_points": ["核心要点1：XXX", "核心要点2：XXX", "核心要点3：XXX"],
          "tags": ["市场趋势", "欧洲"],
          "source": "原始新闻来源",
          "date": "YYYY-MM-DD",
          "original_image_url": "如果原文传入了这个字段的值，请原样保留，如果没有则留空",
          "original_link": "将上文的 Link 原样保留"
        }
      ]
    }
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        return data.get("news", [])

    except Exception as e:
        print(f"Error during AI processing: {e}")
        return []

if __name__ == "__main__":
    test_news = [
        {"title": "UK opens £1.5bn boiler upgrade scheme extension", "source": "BBC News", "published": "2026-04-08 10:00:00"}
    ]
    print(json.dumps(refine_news_with_ai(test_news), ensure_ascii=False, indent=2))
