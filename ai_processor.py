import os
import json
from typing import List, Dict
from openai import OpenAI
import httpx
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
        base_url="https://api.deepseek.com",
        http_client=httpx.Client(
            timeout=httpx.Timeout(180.0, connect=30.0)
        )
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
    4. 确保输出的JSON格式完全合法。千万不要有末尾多余的逗号(Trailing Commas)，禁止保留任何注释。

    你必须以严格的 JSON 格式输出，返回一个包含 "news" 键的字典，"news" 的值是一个对象数组。请按照下述结构输出：
    {
      "news": [
        {
          "headline": "保留原文标题并中文化",
          "rating": "只需输出 'S级', 'A级' 或 'B级' 之一。（S级=改变格局/战略必读，A级=高价值/重要变动，B级=动态参考）",
          "article_type": "填写A/B/C/D/E/F/G/H",
          "one_liner": "一句话结论（说明这篇新闻真正意味着什么）",
          "summary": "事件摘要（谁，什么市场，做了什么事，产品/政策。仅事实，80字内）",
          "deep_analysis": "深度分析（150-250字）：基于「原文事实」进行情报深挖。提取出文中的硬核数据（如参数、投资额、产量、涨跌幅）。【警告：如果原文没有具体数字，绝对禁止捏造或自行推测任何财务、产能或产品参数！】。如果原文缺乏数据，请深度分析其战略意图或行业影响。不要解释你没找到数据，只要呈现你找到的有价值信息即可。",
          "key_info": {
            "公司": "", "品牌": "", "国家": "", "产品名称": "", "类别": "", 
            "制热能力": "", "最高水温": "", "COP_SCOP": "", "冷媒": "", 
            "噪音": "", "电压": "", "上市时间": "", "售价": "", "渠道": "", "目标用户": ""
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
            "theme": "提取新闻的核心英文主题词(如 subsidy, F-gas ban, heat pump installation, etc.)",
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

    import re
    import time

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"     [DeepSeek] 第 {attempt} 次请求 (共 {max_retries} 次)...")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=8192,
                timeout=120
            )
            
            # Clean up markdown code blocks if the LLM adds them
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Simple fix for trailing commas in arrays and objects, extremely common in large LLM JSONs
            content = re.sub(r',\s*([\]}])', r'\1', content)
            
            data = json.loads(content)
            
            return data.get("news", [])

        except Exception as e:
            print(f"     [DeepSeek] 第 {attempt} 次失败: {e}")
            if attempt < max_retries:
                wait_time = attempt * 10
                print(f"     [DeepSeek] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"Error during AI processing after {max_retries} retries: {e}")
                return []

if __name__ == "__main__":
    test_news = [
        {"title": "UK opens £1.5bn boiler upgrade scheme extension", "source": "BBC News", "published": "2026-04-08 10:00:00"}
    ]
    print(json.dumps(refine_news_with_ai(test_news), ensure_ascii=False, indent=2))
