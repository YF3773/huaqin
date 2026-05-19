"""
飞书消息发送模块 - 支持 Webhook 发送
"""
import json
import requests


def send_webhook_message(webhook_url, content, msg_type="text"):
    """通过 Webhook 发送消息"""
    if not webhook_url or webhook_url.strip() == "":
        print("[错误] 未配置 Webhook URL")
        return False

    if not webhook_url.startswith("http"):
        print(f"[错误] Webhook URL 格式无效: {webhook_url[:30]}...")
        return False

    payload = {"msg_type": msg_type}

    if msg_type == "text":
        payload["content"] = {"text": content}
    elif msg_type == "post":
        payload["content"] = content
    elif msg_type == "interactive":
        payload["card"] = content
        payload["msg_type"] = "interactive"
    else:
        payload["content"] = {"text": content}

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        text = resp.text.strip()
        print(f"[调试] 飞书响应状态码: {resp.status_code}, 响应长度: {len(text)}", flush=True)
        if not text:
            print(f"[错误] 飞书返回空响应 (状态码: {resp.status_code})")
            return False
        idx = 0
        while idx < len(text) and text[idx] not in "{[":
            idx += 1
        if idx > 0:
            text = text[idx:]
        if not text:
            print(f"[错误] 飞书响应无有效JSON")
            return False
        result = json.loads(text)
        if result.get("code") == 0:
            print("[OK] 飞书消息发送成功")
            return True
        else:
            print(f"[错误] 飞书发送失败: {result.get('msg', '未知错误')}")
            return False
    except Exception as e:
        print(f"[错误] 飞书发送异常: {e}")
        return False


def build_interactive_card(stock_price, news_list, date_str, stock_name="华勤技术"):
    """构建飞书消息卡片"""
    is_up = True
    change_pct = "--"
    if stock_price and stock_price["change_pct"] != "--":
        try:
            pct_val = float(stock_price["change_pct"].replace("%", "").replace("+", ""))
            is_up = pct_val >= 0
            change_pct = stock_price["change_pct"]
        except:
            pass

    trend_emoji = "📈" if is_up else "📉"
    header_color = "green" if is_up else "red"

    elements = []

    stock_lines = []
    if stock_price:
        stock_lines.append(f"**当前股价：** {stock_price['price']} 元　{trend_emoji} {change_pct}")
        stock_lines.append(f"**今日区间：** {stock_price['low']} ~ {stock_price['high']} 元")
        stock_lines.append(f"**总市值：** {stock_price['total_market_cap']} 亿　**流通市值：** {stock_price['circulating_market_cap']} 亿")
    else:
        stock_lines.append("行情数据暂时无法获取")

    elements.append({
        "tag": "div",
        "text": {
            "tag": "larkdown",
            "content": "\n".join(stock_lines)
        }
    })

    elements.append({"tag": "hr"})

    if news_list:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "larkdown",
                "content": f"**📰 共 {len(news_list)} 条相关新闻**"
            }
        })

        for i, item in enumerate(news_list, 1):
            title = item["title"] or "无标题"
            source = item.get("source", "")
            pub_time = item.get("pub_time", "")
            url = item.get("url", "")

            news_text = f"{i}. **{title}**"
            meta_parts = []
            if source:
                meta_parts.append(f"🔹 {source}")
            if pub_time:
                meta_parts.append(f"⏰ {pub_time}")
            if meta_parts:
                news_text += f"\n   {'　'.join(meta_parts)}"
            if url:
                news_text += f"\n   [🔗 查看原文]({url})"

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "larkdown",
                    "content": news_text
                }
            })
    else:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "larkdown",
                "content": "最近24小时暂无相关新闻。"
            }
        })

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": "🤖 数据来源：东方财富 & 新浪财经　|　仅供参考，不构成投资建议"
            }
        ]
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"{trend_emoji} {stock_name} · 每日新闻汇总（{date_str}）"
            },
            "template": header_color,
        },
        "elements": elements,
    }

    return card


def send_news_report(webhook_url, stock_price, news_list, date_str, stock_name="华勤技术", use_card=True):
    """发送新闻报告到飞书"""
    if use_card:
        card = build_interactive_card(stock_price, news_list, date_str, stock_name)
        return send_webhook_message(webhook_url, card, msg_type="interactive")
    else:
        text_lines = [f"{stock_name} · 每日新闻汇总（{date_str}）"]
        if stock_price:
            text_lines.append(f"股价：{stock_price['price']} 元　{stock_price['change_pct']}")
        text_lines.append("")
        for i, item in enumerate(news_list, 1):
            text_lines.append(f"{i}. [{item['source']}] {item['title']} - {item['pub_time']}")
        return send_webhook_message(webhook_url, "\n".join(text_lines), msg_type="text")
