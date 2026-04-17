import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from typing import List, Dict

def create_news_ppt(news_items: List[Dict], output_file: str = "Weekly_HeatPump_Report.pptx"):
    prs = Presentation()
    
    # Optional: Change slide width/height for 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1. Title Slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "全球热泵与 HVAC 行业资讯周报"
    from datetime import datetime
    subtitle.text = f"自动生成时间：{datetime.now().strftime('%Y-%m-%d')}"
    
    # 2. Content Slides
    blank_slide_layout = prs.slide_layouts[5] # Title only layout, but we'll manually position shapes
    
    for item in news_items:
        slide = prs.slides.add_slide(blank_slide_layout)
        
        # Add Title (adjusted size, no wrap)
        title_shape = slide.shapes.title
        title_shape.text = item.get('headline', '无标题')
        title_shape.text_frame.word_wrap = False
        p = title_shape.text_frame.paragraphs[0]
        p.font.size = Pt(20)
        p.font.bold = True
        p.alignment = PP_ALIGN.LEFT
        
        # Add Image if it exists
        img_path = item.get('image_path')
        if img_path and os.path.exists(img_path):
            try:
                # Add picture on the left side
                pic = slide.shapes.add_picture(img_path, Inches(1), Inches(2), width=Inches(5))
            except Exception as e:
                print(f"Error adding image {img_path}: {e}")
        
        # Add Summary Text
        txBox = slide.shapes.add_textbox(Inches(6.5), Inches(1.5), Inches(6.5), Inches(5.5))
        tf = txBox.text_frame
        tf.word_wrap = True
        
        p = tf.add_paragraph()
        p.text = "【 事件摘要 】"
        p.font.bold = True
        p.font.size = Pt(14)
        
        p = tf.add_paragraph()
        p.text = item.get('summary', '暂无内容。')
        p.font.size = Pt(12)
        p.space_after = Pt(10)
        p.line_spacing = 1.3
        
        tf.add_paragraph() # Spacing
        
        p = tf.add_paragraph()
        p.text = "【 核心要点 】"
        p.font.bold = True
        p.font.size = Pt(14)
        
        for bp in item.get('bullet_points', []):
            p = tf.add_paragraph()
            p.text = f"• {bp}"
            p.font.size = Pt(12)
            p.space_after = Pt(6)
            p.line_spacing = 1.3
            
        tf.add_paragraph() # Spacing
        
        p = tf.add_paragraph()
        p.text = f"▶ 相关标签: {', '.join(item.get('tags', []))}"
        p.font.size = Pt(11)
        p.font.italic = True
        
        p = tf.add_paragraph()
        p.text = f"▶ 来源: {item.get('source', '')}    日期: {item.get('date', '')}"
        p.font.size = Pt(10)
        
        link = item.get('original_link', '')
        if link:
            p = tf.add_paragraph()
            p.text = f"▶ 原文链接: {link}"
            p.font.size = Pt(9)
            p.font.color.rgb = RGBColor(0, 0, 255)
    
    prs.save(output_file)
    print(f"PPT 生成完毕，已保存至 {output_file}")

if __name__ == "__main__":
    # Test
    test_news = [
        {
            "headline": "示例新闻",
            "summary": "这是摘要",
            "tags": ["测试"],
            "source": "Dummy",
            "date": "2026-04-09",
            "image_path": "test_image.png"
        }
    ]
    create_news_ppt(test_news, "test_presentation.pptx")
