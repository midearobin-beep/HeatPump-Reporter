import os
import json
from typing import List, Dict
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# ==========================================
# 模型容灾抽象层 (Model Fallback Abstraction)
# ==========================================
# 三级容灾链：
#   1. gemini-3.1-pro-preview  (Gemini SDK, 付费层, 最高质量)
#   2. gemini-1.5-pro          (Gemini SDK, 付费层, 配额更宽)
#   3. deepseek-chat           (OpenAI 兼容 API, 即 DeepSeek V3 Flash, 外部容灾)

MODEL_CASCADE = [
    {"name": "gemini-3.1-pro-preview", "provider": "gemini"},
    {"name": "gemini-1.5-pro",         "provider": "gemini"},
    {"name": "deepseek-chat",          "provider": "deepseek"},
]


def _call_model(model_cfg: dict, system_prompt: str, user_content: str) -> str:
    """
    统一调用接口，根据 provider 自动分配 SDK。
    返回原始文本响应。
    """
    provider = model_cfg["provider"]
    model_name = model_cfg["name"]

    if provider == "gemini":
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            f"{system_prompt}\n\nInput Data:\n{user_content}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json",
            )
        )
        return response.text.strip()

    elif provider == "deepseek":
        # DeepSeek 使用 OpenAI 兼容接口
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        ds_key = os.getenv("DEEPSEEK_API_KEY")
        if not ds_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in .env")

        client = OpenAI(
            api_key=ds_key,
            base_url="https://api.deepseek.com",
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": f"Input Data:\n{user_content}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    elif provider == "kimi":
        import requests
        
        kimi_key = os.getenv("KIMI_API_KEY")
        if not kimi_key:
            raise RuntimeError("KIMI_API_KEY not set in .env")

        url = "https://api.kimi.com/coding/v1/messages"
        headers = {
            "x-api-key": kimi_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "User-Agent": "ClaudeCode/1.0"
        }
        data = {
            "model": model_name,
            "max_tokens": 8192,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": f"Input Data:\n{user_content}"}
            ]
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"Kimi API Error: {resp.status_code} - {resp.text}")
            
        resp_json = resp.json()
        return resp_json["content"][0]["text"].strip()

    else:
        raise ValueError(f"Unknown provider: {provider}")


def refine_news_with_ai(news_items: List[Dict]) -> List[Dict]:
    """
    Takes a list of fetched news dictionaries, translates and summarizes them
    into structured JSON using the model cascade (Gemini 3.1 Pro -> Gemini 1.5 Pro -> DeepSeek Flash).
    """
    if not news_items:
        return []

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("Warning: GEMINI_API_KEY not set. Skipping Gemini models.")
    else:
        genai.configure(api_key=gemini_key)

    system_prompt = """
    你是「全球热泵行业情报分析引擎（Heat Pump Intelligence Engine）」。

    服务对象：热泵制造商老板、产品经理、海外销售总监、研发负责人、市场战略部门。
    你的任务不是普通新闻摘要，而是把公开文章转化为"可用于商业决策的行业情报"。

    核心原则（必须严格执行）：
    1. 禁止空话套话（如"提升品牌影响力"、"推动行业发展"、"增强消费者信心"），除非文章明确且有依据。
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
          "data_table": {"(中文参数名_带上商业洞察)": "(参数值1)"}, // 必须：提取硬核业务数字。参数名必须全部翻译为中文，并且带有一点商业Insight做修饰（如"极具性价比的售价"、"远超预期的增速"、"令人担忧的高昂年费"等）。若无纯数字参数留空 {}
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

    # 三级容灾链
    # [1] Kimi Coding (kimi-for-coding) - 主力，额度多
    # [2] DeepSeek V4 Pro   - 二备
    # [3] DeepSeek V4 Flash - 三备兜底
    MODEL_CASCADE = [
        {"name": "kimi-for-coding",          "provider": "kimi"},
        {"name": "deepseek-v4-pro",          "provider": "deepseek"},
        {"name": "deepseek-v4-flash",        "provider": "deepseek"},
    ]

    chunk_size = 4  # 每批4篇，降低每日API调用次数
    all_refined_news = []

    # 用 link 建立 continent 回查表（AI处理后恢复地区标签）
    link_to_continent = {item.get('link'): item.get('continent', 'Other') for item in news_items}

    current_model_idx = 0  # 当前使用的模型在 MODEL_CASCADE 中的索引


    for i in range(0, len(news_items), chunk_size):
        chunk = news_items[i:i + chunk_size]
        input_data = json.dumps(chunk, ensure_ascii=False, indent=2)

        max_attempts = 5
        attempt = 0
        chunk_success = False

        while attempt < max_attempts:
            attempt += 1
            if current_model_idx >= len(MODEL_CASCADE):
                break
                
            model_cfg = MODEL_CASCADE[current_model_idx]
            model_name = model_cfg["name"]
            total_batches = (len(news_items) + chunk_size - 1) // chunk_size
            print(f"     [{model_name}] 处理批次 {i//chunk_size + 1} (共 {total_batches} 批) - 第 {attempt} 次请求...")

            try:
                raw = _call_model(model_cfg, system_prompt, input_data)

                # 清洗可能的 Markdown 代码块包裹
                content = raw
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
                        # 回填 continent（AI不负责保留此字段）
                        n["continent"] = link_to_continent.get(n.get("original_link"), "Other")
                    all_refined_news.extend(batch_data["news"])

                chunk_success = True
                break

            except Exception as e:
                err_str = str(e).lower()
                # 切换触发条件：配额超限(429) | 模型不可用(404/400) | 鉴权失败(401) | 服务超时(503/504) | 连接失败 | 区域限制
                is_cascade_error = (
                    "429" in err_str or "404" in err_str or "400" in err_str or "401" in err_str
                    or "503" in err_str or "504" in err_str or "quota" in err_str
                    or "rate limit" in err_str or "not found" in err_str
                    or "location" in err_str or "authentication" in err_str
                    or "connection" in err_str or "deadline" in err_str
                    or "timeout" in err_str or "handshak" in err_str
                    or "remote end closed" in err_str or "aborted" in err_str
                    or "remotedisconnected" in err_str or "invalid_authentication_error" in err_str
                )
                if is_cascade_error and current_model_idx < len(MODEL_CASCADE) - 1:
                    current_model_idx += 1
                    next_cfg = MODEL_CASCADE[current_model_idx]
                    print(f"     [配额耗尽/限速] 自动切换至备用模型: {next_cfg['name']} ({next_cfg['provider']})")
                    attempt -= 1  # 不消耗重试次数，直接用新模型重试
                    continue

                print(f"     [AI] 批次 {i//chunk_size + 1} 第 {attempt} 次失败: {err_str[:150]}")
                if attempt < max_retries:
                    wait_time = attempt * 10
                    print(f"     [AI] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"Error during AI processing for batch {i//chunk_size + 1} after {max_retries} retries.")

        if not chunk_success:
            continue

    return all_refined_news
