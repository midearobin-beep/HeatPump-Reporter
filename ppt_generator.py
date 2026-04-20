import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from typing import List, Dict
from datetime import datetime

def create_news_ppt(news_items: List[Dict], output_file: str = "Weekly_HeatPump_Report.pptx"):
    prs = Presentation()
    
    # 16:9 Aspect Ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1. Title Slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "全球热泵与 HVAC 行业商业情报周报\n(Commercial Intelligence Briefing)"
    subtitle.text = f"自动生成时间：{datetime.now().strftime('%Y-%m-%d')}"
    
    blank_slide_layout = prs.slide_layouts[5]

    for item in news_items:
        # ==========================================
        # SLIDE 1: Executive Summary & Table
        # ==========================================
        slide1 = prs.slides.add_slide(blank_slide_layout)
        
        # Title
        title_shape = slide1.shapes.title
        title_text = f"[{item.get('article_type', 'X')}] {item.get('headline', '无标题')}"
        title_shape.text = title_text
        title_shape.text_frame.word_wrap = False
        p = title_shape.text_frame.paragraphs[0]
        p.font.size = Pt(18)
        p.font.bold = True
        p.alignment = PP_ALIGN.LEFT

        # Image (Left side)
        img_path = item.get('image_path')
        if img_path and os.path.exists(img_path):
            try:
                slide1.shapes.add_picture(img_path, Inches(0.5), Inches(1.5), width=Inches(5))
            except Exception as e:
                print(f"Error adding image {img_path}: {e}")

        # Text Box (Right side)
        txBox1 = slide1.shapes.add_textbox(Inches(5.8), Inches(1.2), Inches(7.0), Inches(6.0))
        tf1 = txBox1.text_frame
        tf1.word_wrap = True

        # Rating & One-Liner
        p = tf1.add_paragraph()
        p.text = f"♦ 情报等级: {item.get('rating', 'N/A')} | {item.get('one_liner', '')}"
        p.font.bold = True
        p.font.color.rgb = RGBColor(180, 0, 0)
        p.font.size = Pt(14)
        
        tf1.add_paragraph()
        
        # Summary
        p = tf1.add_paragraph()
        p.text = "【事件摘要】"
        p.font.bold = True
        p.font.size = Pt(12)
        p = tf1.add_paragraph()
        p.text = item.get('summary', '暂无内容。')
        p.font.size = Pt(11)
        
        tf1.add_paragraph()

        # Key Info "Table" (Formatted lines)
        p = tf1.add_paragraph()
        p.text = "【关键参数提取】"
        p.font.bold = True
        p.font.size = Pt(12)

        key_info = item.get("key_info", {})
        if key_info:
            for k, v in key_info.items():
                if v and str(v).strip() and "未披露" not in str(v):
                    p = tf1.add_paragraph()
                    p.text = f" • {k}: {v}"
                    p.font.size = Pt(10)
        else:
            p = tf1.add_paragraph()
            p.text = " • 文中未披露明确参数"
            p.font.size = Pt(10)

        # Source Links
        tf1.add_paragraph()
        p = tf1.add_paragraph()
        p.text = f"▶ 来源: {item.get('source', '')} | 日期: {item.get('date', '')}"
        p.font.size = Pt(9)
        link = item.get('original_link', '')
        if link:
            p = tf1.add_paragraph()
            p.text = f"▶ 原文链接: {link}"
            p.font.size = Pt(9)
            p.font.color.rgb = RGBColor(0, 0, 255)

        # ==========================================
        # SLIDE 2: Commercial Intelligence Deep Dive
        # ==========================================
        slide2 = prs.slides.add_slide(blank_slide_layout)
        
        # Subtitle linking to main headline
        title_shape2 = slide2.shapes.title
        title_shape2.text = f"↳ 商业情报洞察: {item.get('headline', '无标题')[:40]}..."
        p2 = title_shape2.text_frame.paragraphs[0]
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.alignment = PP_ALIGN.LEFT
        p2.font.color.rgb = RGBColor(100, 100, 100)

        txBox2 = slide2.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(12.0), Inches(6.0))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True

        # Hidden Signals
        p = tf2.add_paragraph()
        p.text = "【隐藏信号 (Hidden Signals)】"
        p.font.bold = True
        p.font.size = Pt(14)
        for sig in item.get('hidden_signals', []):
            p = tf2.add_paragraph()
            p.text = f"  - {sig}"
            p.font.size = Pt(12)
        tf2.add_paragraph()

        # Competitor Impact
        p = tf2.add_paragraph()
        p.text = "【竞品影响 (Competitor Impact)】"
        p.font.bold = True
        p.font.size = Pt(14)
        impacts = item.get('competitor_impact', {})
        for region, lines in impacts.items():
            if lines:
                p = tf2.add_paragraph()
                p.text = f"  ♦ {region}:"
                p.font.bold = True
                p.font.size = Pt(11)
                for line in lines:
                    p = tf2.add_paragraph()
                    p.text = f"    - {line}"
                    p.font.size = Pt(11)
        tf2.add_paragraph()

        # Follow-up Suggestions
        p = tf2.add_paragraph()
        p.text = "【建议追踪点 (Follow-ups)】"
        p.font.bold = True
        p.font.size = Pt(14)
        for sug in item.get('suggestions', []):
            p = tf2.add_paragraph()
            p.text = f"  - {sug}"
            p.font.size = Pt(12)
        tf2.add_paragraph()

        # Executable Actions
        p = tf2.add_paragraph()
        p.text = "【可执行动作 (Actionable Operations)】"
        p.font.bold = True
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(180, 0, 0)
        for act in item.get('actions', []):
            p = tf2.add_paragraph()
            p.text = f"  - {act}"
            p.font.size = Pt(12)
            p.font.bold = True

    prs.save(output_file)
    print(f"PPT 生成完毕，已保存至 {output_file}")

if __name__ == "__main__":
    # Test Data Array matching the new C-level strict json
    test_news = [
        {
            "headline": "测试: 大金发布新型高水温热泵",
            "rating": "9",
            "article_type": "A",
            "one_liner": "大金正试图用不需要管道改造的高温热泵强吃欧洲的传统燃气锅炉存量市场。",
            "summary": "大金在欧洲市场推出第三代针对家庭供暖的高温热泵，最高水温可达70度，无需更换旧型号暖气片，直指英国和德国市场。",
            "key_info": {
                "国家": "欧洲/英国",
                "品牌": "Daikin",
                "高级水温": "70度",
                "售卖渠道": "文中未披露"
            },
            "hidden_signals": [
                "高温机型抢替代锅炉市场已经成为绝对主流",
                "日系企业开始在欧洲大范围吃补贴红利"
            ],
            "competitor_impact": {
                "对中国制造商": ["警惕其对低端产品的降维打击", "研发需要加快跟进高温冷媒"],
                "对本公司": ["销售资料中加入对此款机型的对比参数"]
            },
            "suggestions": ["关注是否使用R290", "关注最终定价"],
            "actions": ["产品一部：调取大金最新说明书评估参数"],
            "date": "2026-04-10",
            "original_link": "https://example.com"
        }
    ]
    create_news_ppt(test_news, "test_presentation.pptx")
