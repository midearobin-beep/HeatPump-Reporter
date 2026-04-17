# HeatPump-Reporter

An automated multi-lingual reporting pipeline specializing in the Heat Pump (HVAC) industry. This system continuously monitors Google News across multiple languages (English, German, French, Italian, Spanish), refines the content using DeepSeek AI to generate business-oriented summaries, fetches original images (or uses AI image generation as fallback via MiniMax), and outputs an automated weekly Microsoft PowerPoint report.

## Features

* **Multi-Lingual Monitoring**: Simultaneously tracks policy and market trends in the US/UK, Germany, France, Italy, and Spain.
* **DeepSeek AI Summarization**: Synthesizes disparate news articles into concise, structured bullet points and integrates duplicated news.
* **Smart Image Extraction**: Intercepts Google News short links, automatically parses raw sites to extract actual `<meta og:image>` cover images, and safely converts WebP formats for PPT.
* **Dynamic Configuration**: Fully customizable tracking keywords and ranges via `config.yaml`.
* **Automated Weekly Outputs**: Titles generated PPT files by ISO calendar weeks (e.g. `2026CW15_HeatPump_Weekly_Report.pptx`) with optimized font layouts and internal link citations.

---

## 🛠 Prerequisites

1. **Python 3.9+**
2. An active **DeepSeek API Key**
3. An active **MiniMax API Key** (for fallback AI image generation)

## 🚀 Quick Start Configuration

### 1. Configure the Environment
Clone the repository and jump into it:

```bash
cd HeatPump-Reporter
```

Create a `.env` file in the root directory. **Note: Do not commit this file to version control.**

```env
# .env 配置文件
DEEPSEEK_API_KEY=sk-xxxxxx
MINIMAX_API_KEY=sk-xxxxxx
```

### 2. Install Dependences
Create an isolated Python virtual environment, activate it, and install required libraries:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Customize Search Target (`config.yaml`)
Open `config.yaml` to dynamically maintain your search vocabulary and locales. 
You can add specific regional queries or search syntax for specific websites, e.g.:
```yaml
- query: '("Heat pump") AND ("subsidy" OR "policy")'
  lang: "English (US/UK/EU)"
  params: "&hl=en-US&gl=US&ceid=US:en"
```

## 🖥 How to Run

### Manual Run
Ensure your virtual environment is activated, then simply execute:
```bash
python main.py
```
A new PowerPoint presentation (e.g., `2026CW15_HeatPump_Weekly_Report.pptx`) will be generated.

### Local Automation (macOS / Linux)
We provide a standalone bash script `run_report.sh` that loads correct paths before launching Python. You can register this to your `crontab`. Example command to make it run every Friday at 17:30:

```bash
30 17 * * 5 /bin/bash /absolute/path/to/HeatPump-Reporter/run_report.sh
```

### GitHub Actions (Cloud Automation)
If pushed to a GitHub repository, an action configuration is included in `.github/workflows/ppt_generator.yml` which executes automatically on Fridays. Ensure you add `DEEPSEEK_API_KEY` and `MINIMAX_API_KEY` to your repository's **Secrets**. The workflow features a built-in auto-commit to track `history.json` and prevent duplicate news in recurring generations.

---
*Powered by DeepSeek V3, MiniMax, python-pptx, and googlenewsdecoder*
