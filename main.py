import sys
sys.stdout.reconfigure(encoding="utf-8")

"""
华勤技术股价播报机器人
"""

import os
from datetime import datetime, timedelta, timezone

from news_fetcher import fetch_stock_price, fetch_all_news
from feishu_sender import send_webhook_message, send_news_report

CST = timezone(timedelta(hours=8))

WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
STOCK_CODE = os.environ.get("STOCK_CODE", "603296")
STOCK_NAME = os.environ.get("STOCK_NAME", "华勤技术")
NEWS_HOURS_BACK = int(os.environ.get("NEWS_HOURS_BACK", "24"))
NEWS_MAX_COUNT = int(os.environ.get("NEWS_MAX_COUNT", "20"))


def main():
    today = datetime.now(CST).strftime("%Y年%m月%d日")
    print(f"开始查询 {STOCK_NAME}({STOCK_CODE}) 实时股价和新闻...", flush=True)

    stock_price = fetch_stock_price(STOCK_CODE)
    if stock_price:
        print(f"股价: {stock_price['price']} 元 ({stock_price['change_pct']})", flush=True)
    else:
        print("股价查询失败，继续获取新闻...", flush=True)

    print("开始获取新闻...", flush=True)
    news_list = fetch_all_news(STOCK_CODE, STOCK_NAME, NEWS_HOURS_BACK, NEWS_MAX_COUNT)
    print(f"共获取到 {len(news_list)} 条新闻", flush=True)

    print("发送飞书消息...", flush=True)
    success = send_news_report(WEBHOOK_URL, stock_price, news_list, today, stock_name=STOCK_NAME, use_card=True)
    if success:
        print("发送完成！", flush=True)
    else:
        print("发送失败！", flush=True)


if __name__ == "__main__":
    main()
