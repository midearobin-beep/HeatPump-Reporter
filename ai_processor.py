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
    你是「全球热泵行业情报分析引擎（Heat Pump Intelligence Engine）」。

    服务对象：热泵制造商老板、产品经理、海外销售总监、研发负责人、市场战略部门。
    你的任务不是普通新闻摘要，而是把公开文章转化为“可用于商业决策的行业情报”。

    核心原则（必须严格执行）：
    1. 禁止空话套话（如“提升品牌影响力”、“推动行业发展”、“增强消费者信心”），除非文章明确且有依据。
    2. 信息密度优先：每段要包含具体信息、判断、事实、数字、参数、动作。
    3. 自动识别文章类型（必须先判断）：
       A. 新品发布/产品升级, B. 企业战略/投资扩产, C. 法规政策/补贴, D. 奖项宣传/品牌营销, 
       E. 技术趋势/行业研究, F. 渠道合作/市场进入, G. 财报/经营数据, H. 其他

    你必须以严格的 JSON 格式输出，返回一个包含 "news" 键的字典，"news" 的值是一个对象数组。请按照下述结构输出：
    {
      "news": [
        {
          "headline": "保留原文标题并中文化",
          "rating": "1级-10级之间评分，按对企业参考价值（1-3水文，4-6普通资讯，7-8行业价值，9-10高价值）",
          "article_type": "填写A/B/C/D/E/F/G/H",
          "one_liner": "一句话结论（说明这篇新闻真正意味着什么）",
          "summary": "事件摘要（谁，什么市场，做了什么事，产品/政策。仅事实，80字内）",
          "key_info": {
            "公司": "", "品牌": "", "国家": "", "产品名称": "", "类别": "", 
            "制热能力": "", "高级水温": "", "COP_SCOP": "", "冷媒": "", 
            "噪音": "", "电压": "", "上市时间": "", "售价": "", "渠道": "", "目标用户": ""
            // 如未给出参数请填“文中未披露”，如为合理推断请加【推测】
          },
          "hidden_signals": [
            "从行业视角判断背后的动作1",
            "信号2（必须具体，禁空话，限3-5条）"
          ],
          "competitor_impact": {
            "对中国制造商": ["影响1", "影响2"],
            "对欧洲品牌": ["影响1"],
            "对本公司": ["动作或启示1"]
          },
          "suggestions": ["应该跟踪是否进入欧洲", "看是否切冷媒 (未来关注点)"],
          "actions": ["调研参数", "销售部门动作等"],
          "analysis": {
            "category": "政策法规|企业新闻|产品发布|技术突破|市场趋势|安装案例|能源价格|环保议题 (选择1一项)",
            "country": "提取涉及的主要国家英语名称(如 Germany, UK, France, etc.)",
            "theme": "提取新闻的心英文主题词(如 subsidy, F-gas ban, heat pump installation, etc.)",
            "target": "residential|commercial|industrial|utility (选择1项)",
            "tone": "positive|neutral|serious (选择1项)"
          },
          "source": "原始新闻来源",
          "date": "YYYY-MM-DD",
          "original_image_url": "原样保留或留空",
          "original_link": "原样保留原来link字段的值"
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
