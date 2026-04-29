"""
reprocess_april28.py
重新生成 2026-04-28 的日报（昨日因 Gemini 配额耗尽导致 AI 处理全部失败）
"""

import os
import json
from news_fetcher import extract_full_text, extract_og_image, detect_continent_from_url
from ai_processor import refine_news_with_ai
from image_fetcher import fetch_image, download_original_image
from ppt_generator import create_news_ppt

TARGET_DATE = "2026-04-28"
OUTPUT_PPT  = f"{TARGET_DATE}_HeatPump_Daily_Briefing.pptx"

# 昨日失败时已抓取的 URL 列表（从 history.json 末尾截取的已知 Apr 28 批次）
# 这批 URL 是昨日 cron job 抓取到但 AI 处理全部失败的那批
KNOWN_APR28_URLS = [
    "https://www.achrnews.com/articles/166128-new-daikin-air-to-water-heat-pump",
    "https://www.thecooldown.com/green-tech/carrier-invests-in-heat-geek-accelerate-adoption/",
    "https://www.indexbox.io/blog/residential-air-to-air-heat-pump-market-forecast-points-higher-toward-2035/",
    "https://holodindustry.ru/news/company-news/lg-predstavila-lineyku-hvac-oborudovaniya-dlya-evropy/",
    "https://www.ixbt.com/live/chome/kompaniya-samsung-zanyala-liderskie-pozicii-v-evropeyskom-reytinge-kondicionerov.html",
    "https://www.iscihaber.net/dunya/almanyada-isi-pompasi-projesi-hannoverde-13-bin-konut-atik-su-ile-isinacak/",
    "https://www.takagazete.com.tr/kombilerin-devri-sona-eriyor-isinma-icin-devrim-zamani/amp",
    "https://www.acrjournal.uk/heat-pumps/high-temperature-heat-pumps-the-key-to-non-disruptive-retrofits/",
    "https://www.msn.com/en-us/lifestyle/home-and-garden/hvac-giant-bets-big-on-accelerating-global-heat-pump-adoption/ar-AA1EOnUY",
    "https://www.openpr.com/news/4489964/india-hvac-market-49b-boom-driven-by-smart-cities-and-strict",
    "https://www.hvnplus.co.uk/news/industry-expert-publishes-heat-pump-guide-as-demand-surges-by-70-27-04-2026/",
    "https://www.pv-magazine.com/2026/04/27/uk-startup-showcases-all-in-one-water-cylinder-heat-pump-prototype/",
    "https://www.achrnews.com/articles/166127-american-energy-dominance-act-what-it-means-for-hvac",
    "https://www.solarserver.de/2026/04/27/beg-heizungsfoerderung-der-kfw-interesse-an-waermepumpe-steigt/",
    "https://www.neozone.org/innovation/blueheart-energy-teste-sa-pompe-a-chaleur-thermoacoustique-en-milieu-reel/",
    "https://rmc.bfmtv.com/conso/video-comment-payer-sa-pompe-a-chaleur-moins-cher_VN-202604270555.html",
    "https://www.buildnews.it/articolo/midea-porta-il-confronto-oltre-la-fiera-con-mce-next-green-vision-2030/",
    "https://elettricomagazine.it/news-tecnologia/aqua-g-evo-pompa-di-calore-r290-retrofit-commerciale/",
    "https://www.infobuildenergia.it/info_dalle_aziende/panasonic-pompe-calore-refrigeranti-transizione-energetica/",
    "https://www.elcorreo.com/content-local/de-palacio-del-siglo-xvii-a-confort-cinco-estrellas-con-la-geotermia/noticia/2026/04/27/",
    "https://www.warmte365.nl/nieuws/warmtepomp-als-geopolitiek-wapen-europa-zoekt-energieonafhankelijkheid/",
    "https://www.4green.gr/news/data/fwtoboltaika/meiosi-fpa-fotovoltaika-antlies-thermotitas_163823.asp",
    "https://www.coolingpost.com/training/exploring-why-heat-pumps-can-underperform/",
    "https://climateinstitute.ca/how-governments-can-help-canadian-households-electrify-cleaner-and-more-affordably/",
    "https://www.chathamhouse.org/2026/04/norway-can-teach-uk-about-energy-security-lesson-not-more-north-sea-drilling",
    "https://elementallondon.show/news/heat-pump-water-heaters-help-create-sustainable-environment-for-new-builds/",
    "https://holodindustry.ru/news/new-equipment/trane-rasshiryaet-lineyku-vozdukhookhlazhdaemykh-chillerov-s-vintovym-kompressorom/",
    "https://shopping.yahoo.com/home-garden/home-improvement/articles/reporter-addresses-hype-behind-novel-heat-pump-technology-thermo/",
    "https://www.lehighvalleylive.com/easton/2026/04/the-air-conditioner-broke-last-year-now-easton-area-school-district-is-replacing-hvac-systems.html",
    "https://www.thedailyscrumnews.com/how-work-from-home-trends-are-changing-hvac-choices/",
]


def main():
    output_ppt = OUTPUT_PPT

    # 删除昨日生成的空壳 PPT（29KB），强制重新生成
    if os.path.exists(output_ppt):
        size_kb = os.path.getsize(output_ppt) // 1024
        if size_kb < 500:
            print(f"⚠ 发现空壳 PPT ({size_kb}KB)，删除并重新生成...")
            os.remove(output_ppt)
        else:
            print(f"✅ {output_ppt} 已存在且大小正常 ({size_kb}KB)，跳过。")
            return

    print(f"📰 准备重新处理 {TARGET_DATE} 的 {len(KNOWN_APR28_URLS)} 篇文章...\n")

    news_to_ai = []
    os.makedirs("assets", exist_ok=True)

    for i, url in enumerate(KNOWN_APR28_URLS):
        print(f"  [{i+1}/{len(KNOWN_APR28_URLS)}] 抓取全文: {url[:80]}...")
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                print("     → 无法下载，跳过")
                continue

            meta = trafilatura.extract_metadata(downloaded)
            title = meta.title if meta and meta.title else "Unknown"
            full_text = trafilatura.extract(downloaded) or ""
            og_img = extract_og_image(url)

            news_to_ai.append({
                "title": title,
                "link": url,
                "published": TARGET_DATE,
                "source": url.split("/")[2].replace("www.", ""),
                "language": "auto",
                "continent": detect_continent_from_url(url, fallback="Other"),
                "original_image_url": og_img,
                "summary": full_text[:8000],  # 截断避免超长
            })
        except Exception as e:
            print(f"     → 错误: {e}")

    print(f"\n✅ 成功抓取 {len(news_to_ai)} 篇文章，开始 AI 处理...\n")

    refined = refine_news_with_ai(news_to_ai)
    print(f"\n🤖 AI 处理完成，保留 {len(refined)} 篇有效情报。\n")

    # 配图
    for idx, item in enumerate(refined):
        img_path = f"assets/regen_{TARGET_DATE}_{idx}.png"
        og_url = item.get("original_image_url")
        success = False
        if og_url:
            success = download_original_image(og_url, img_path)
        if not success:
            fetch_image(item.get("analysis", {}), img_path)
        item["image_path"] = img_path

    create_news_ppt(refined, output_ppt)
    size_mb = os.path.getsize(output_ppt) / 1024 / 1024
    print(f"\n🎉 完成! 报告已保存: {os.path.abspath(output_ppt)} ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
