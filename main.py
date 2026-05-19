import sys
sys.stdout.reconfigure(encoding="utf-8")

"""
华勤技术股价播报机器人 - 仅推送收盘日报
"""

import os
from datetime import datetime, timezone, timedelta

from news_fetcher import fetch_stock_price
from feishu_sender import send_webhook_message

CST = timezone(timedelta(hours=8))

WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
STOCK_CODE = os.environ.get("STOCK_CODE", "603296")
STOCK_NAME = os.environ.get("STOCK_NAME", "华勤技术")
BUY_PRICE = float(os.environ.get("BUY_PRICE", "116.03"))
SHARES = int(os.environ.get("SHARES", "100"))


def build_price_report(stock_price):
    today = datetime.now(CST).strftime("%Y-%m-%d")
    if not stock_price:
        return f"⚠️ {STOCK_NAME} 行情数据暂时无法获取"

    try:
        price = float(stock_price["price"])
        pct_str = stock_price["change_pct"]
        pct_val = float(pct_str.replace("%", "").replace("+", ""))
    except:
        return f"⚠️ {STOCK_NAME} 行情数据异常"

    low = stock_price.get("low", "--")
    high = stock_price.get("high", "--")

    total_cost = BUY_PRICE * SHARES
    market_value = round(price * SHARES, 2)
    pnl = round(market_value - total_cost, 2)
    pnl_pct = round((price - BUY_PRICE) / BUY_PRICE * 100, 2)
    pnl_emoji = "🔴" if pnl < 0 else "🟢"

    lines = [
        f"📊 {STOCK_NAME} 收盘日报",
        "━━━━━━━━━━━━━━━━",
        f"📅 日期：{today}",
        "",
        f"💰 收盘价：**{price} 元**",
        f"📉 涨跌幅：{pct_val:+.2f}%",
        f"📈 今日区间：{low} ~ {high}",
        "",
        "━━━━━━━━━━━━━━━━",
        f"{pnl_emoji} 浮动盈亏：**{pnl:+.2f} 元** ({pnl_pct:+.2f}%)",
        f"💼 持仓市值：{market_value} 元",
        f"💳 初始投入：{total_cost} 元",
        "━━━━━━━━━━━━━━━━",
        f"📊 买入价：{BUY_PRICE} | {SHARES} 股",
    ]
    return "\n".join(lines)


def main():
    print(f"开始查询 {STOCK_NAME}({STOCK_CODE}) 行情...", flush=True)

    stock_price = fetch_stock_price(STOCK_CODE)
    if stock_price:
        print(f"股价: {stock_price['price']} 元 ({stock_price['change_pct']})", flush=True)
    else:
        print("股价查询失败", flush=True)

    print("发送飞书消息...", flush=True)
    text = build_price_report(stock_price)
    success = send_webhook_message(WEBHOOK_URL, text, msg_type="text")
    if success:
        print("发送完成！", flush=True)
    else:
        print("发送失败！", flush=True)


if __name__ == "__main__":
    main()
