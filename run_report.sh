#!/bin/bash

# 加载环境变量（防止 cron 找不到环境）
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

# 进入项目目录
cd /Users/robinwang/Coding/HeatPump-Reporter

# 激活虚拟环境并执行
source venv/bin/activate
python main.py >> /Users/robinwang/Coding/HeatPump-Reporter/cron_run.log 2>&1
