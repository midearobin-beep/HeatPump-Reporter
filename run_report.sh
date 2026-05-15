#!/bin/bash

# 加载环境变量（防止 cron 找不到环境）
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

# 进入项目目录
cd /Users/robinwang/Coding/HeatPump-Reporter

# 激活虚拟环境并执行
source venv/bin/activate
python3 -u main.py >> /Users/robinwang/Coding/HeatPump-Reporter/cron_run.log 2>&1

# 自动备份生成的日报到微盘
DEST_DIR="/Users/robinwang/Library/Containers/com.tencent.WeWorkMac/Data/WeDrive/万居隆集团/我的文件/行业新闻政策趋势日报"
echo "开始备份报告到: $DEST_DIR" >> /Users/robinwang/Coding/HeatPump-Reporter/cron_run.log
rsync -a /Users/robinwang/Coding/HeatPump-Reporter/*_HeatPump_Daily_Briefing.pptx "$DEST_DIR/" >> /Users/robinwang/Coding/HeatPump-Reporter/cron_run.log 2>&1
rsync -a /Users/robinwang/Coding/HeatPump-Reporter/*_HeatPump_Weekly_Report.pptx "$DEST_DIR/" >> /Users/robinwang/Coding/HeatPump-Reporter/cron_run.log 2>&1 || true
echo "备份完成" >> /Users/robinwang/Coding/HeatPump-Reporter/cron_run.log

