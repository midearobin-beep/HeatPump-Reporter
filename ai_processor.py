import os
import json
from typing import List, Dict
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def refine_news_with_ai(news_items: List[Dict]) -> List[Dict]:
    """
    Takes a list of fetched news dictionaries, translates and summarizes them
    into a structured JSON array format using Google Gemini 3.1 Pro.
    """
    if not news_items:
        return []

    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not set. Falling back to dummy data.")
        return []

    genai.configure(api_key=api_key)
    # Model cascade: start with Gemini 3.1 Pro (best quality), fall back to 1.5 Pro on quota errors
    MODEL_CASCADE = [
        'gemini-3.1-pro-preview',
        'gemini-1.5-pro',
    ]
    # Find which model to start with (check if we already switched during this run)
    primary_model_name = MODEL_CASCADE[0]
    model = genai.GenerativeModel(primary_model_name)
    current_model_idx = 0

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
    4. 确保输出的JSON格式完全合法。

    你必须以严格的 JSON 格式输出，返回一个包含 "news" 键的字典，"news" 的值是一个对象数组。请按照下述结构输出：
    {
      "news": [
        {
          "headline": "保留原文标题并中文化",
          "rating": "只需输出 'S级', 'A级' 或 'B级' 之一。（S级=改变格局/战略必读，A级=高价值/重要变动，B级=动态参考）",
          "article_type": "填写A/B/C/D/E/F/G/H",
          "one_liner": "一句话结论（说明这篇新闻真正意味着什么）",
          "summary": "事件摘要（谁，什么市场，做了什么事，产品/政策。仅事实，80字内）",
          "deep_analysis": "深度分析（150-250字）：基于「原文事实」进行情报深挖。深度推演其战略意图或行业影响。不要解释你没找到数据，只要呈现有价值信息。\n【警告：如果原文没有具体数字，绝对禁止捏造！】",
          "data_table": {"(中文参数名_带上商业洞察)": "(参数值1)"}, // 必须：提取硬核业务数字。参数名必须全部翻译为中文，并且带有一点商业Insight做修饰（如“极具性价比的售价”、“远超预期的增速”、“令人担忧的高昂年费”等）。若无纯数字参数留空 {}
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

    chunk_size = 4  # Increased from 2 to reduce daily API call count
    all_refined_news = []
    
    # Create a lookup for continent based on link
    link_to_continent = {item.get('link'): item.get('continent', 'Other') for item in news_items}
    
    for i in range(0, len(news_items), chunk_size):
        chunk = news_items[i:i + chunk_size]
        input_data = json.dumps(chunk, ensure_ascii=False, indent=2)
        
        max_retries = 3
        chunk_success = False
        
        for attempt in range(1, max_retries + 1):
            try:
                model_name = MODEL_CASCADE[current_model_idx]
                print(f"     [{model_name}] 处理批次 {i//chunk_size + 1} (共 {(len(news_items) + chunk_size - 1)//chunk_size} 批) - 第 {attempt} 次请求...")
                
                response = model.generate_content(
                    f"{system_prompt}\n\nInput Data:\n{input_data}",
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json",
                    )
                )
                
                content = response.text.strip()
                # Simple fix for potential markdown wrapping
                if content.startswith("```json"):
                    content = content[7:]
                elif content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                batch_data = json.loads(content)
                if "news" in batch_data:
                    for n in batch_data["news"]:
                        # Re-attach continent based on link
                        n["continent"] = link_to_continent.get(n.get("original_link"), "Other")
                    all_refined_news.extend(batch_data["news"])
                
                chunk_success = True
                break
            except Exception as e:
                err_str = str(e)
                # Detect quota exhaustion and switch model
                if "429" in err_str and current_model_idx < len(MODEL_CASCADE) - 1:
                    current_model_idx += 1
                    new_model_name = MODEL_CASCADE[current_model_idx]
                    print(f"     [配额耗尽] 切换至备用模型: {new_model_name}")
                    model = genai.GenerativeModel(new_model_name)
                    # Don't count this as a retry, just switch and retry immediately
                    attempt -= 1
                    continue
                print(f"     [AI] 批次 {i//chunk_size + 1} 第 {attempt} 次失败: {err_str[:120]}")
                if attempt < max_retries:
                    wait_time = attempt * 10
                    print(f"     [AI] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"Error during AI processing for batch {i//chunk_size + 1} after {max_retries} retries.")
        
        if not chunk_success:
            continue
            
    return all_refined_news
