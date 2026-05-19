"""
新闻抓取模块 - 从东方财富和新浪财经获取华勤技术相关新闻
"""
import json
import re
import time
import urllib.parse
import requests
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))


def fetch_eastmoney_news(stock_code="603296", page_size=20):
    """从东方财富获取个股新闻（尝试多个接口）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://guba.eastmoney.com/",
    }
    proxies = {"http": None, "https": None}

    search_param = {
        "uid": "",
        "keyword": stock_code,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": 1,
                "pageSize": page_size,
                "preTag": "",
                "postTag": "",
                "needPreTag": True
            }
        }
    }

    apis = [
        {"url": "https://push2.eastmoney.com/api/qt/article/list", "params": {"secuCode": stock_code, "secuMarket": "1", "pageNum": 1, "pageSize": page_size}},
        {"url": "https://search-api-web.eastmoney.com/search/jsonp", "params": {"cb": "", "param": json.dumps(search_param)}},
        {"url": "https://push.eastmoney.com/api/qt/article/list", "params": {"secuCode": stock_code, "secuMarket": "1", "pageNum": 1, "pageSize": page_size}},
    ]

    data = None
    for api in apis:
        try:
            resp = requests.get(api["url"], params=api["params"], headers=headers, timeout=10, proxies=proxies)
            text = resp.text.strip()
            if not text:
                continue
            if text.startswith("jQuery"):
                match = re.search(r'\(([\s\S]+)\)\s*$', text)
                if match:
                    text = match.group(1)
            data = json.loads(text)
            if data:
                break
        except Exception as e:
            print(f"[调试] 东方财富接口 {api['url']} 失败: {e}", flush=True)
            data = None
            continue

    if not data:
        print("[警告] 东方财富所有接口均失败", flush=True)
        return []

    articles = []
    if "data" in data and isinstance(data["data"], list):
        articles = data["data"]
    elif "list" in data:
        articles = data["list"]
    elif "result" in data and "list" in data.get("result", {}):
        articles = data["result"]["list"]

    results = []
    for art in articles:
        if not art:
            continue
        pub_time = art.get("showTime", art.get("createTime", art.get("date", "")))
        if pub_time:
            try:
                pub_time = int(pub_time) / 1000
                pub_dt = datetime.fromtimestamp(pub_time, tz=CST)
            except:
                continue
        else:
            continue

        title = art.get("title", "") or art.get("articleTitle", "") or art.get("ArticleTitle", "")
        summary = art.get("summary", "") or art.get("introduction", "") or art.get("intro", "")
        art_url = art.get("url", "") or art.get("artUrl", "") or art.get("articleUrl", "") or art.get("contentUrl", "")

        results.append({
            "title": title,
            "summary": summary,
            "source": "东方财富",
            "url": art_url,
            "pub_time": pub_dt.strftime("%Y-%m-%d %H:%M"),
            "timestamp": pub_dt.timestamp(),
        })

    return results


def fetch_sina_news(stock_code="603296"):
    """从新浪财经获取个股新闻（尝试多个接口）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    proxies = {"http": None, "https": None}
    results = []

    json_url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/News_ServiceNews?num=20&page=1&symbol=sh{stock_code}"
    try:
        resp = requests.get(json_url, headers=headers, timeout=10, proxies=proxies)
        if resp.text.strip():
            text = resp.text.strip()
            if text.startswith("/*") or text.startswith("//"):
                text = re.sub(r'^(/\*[\s\S]*?\*/|//[^\n]*\n)', '', text).strip()
            news_items = json.loads(text)
            if isinstance(news_items, list):
                for item in news_items:
                    pub_str = item.get("date", item.get("time", ""))
                    try:
                        pub_dt = datetime.strptime(pub_str, "%Y-%m-%d %H:%M")
                        pub_dt = pub_dt.replace(tzinfo=CST)
                    except:
                        pub_dt = datetime.now(CST)
                    results.append({
                        "title": item.get("title", ""),
                        "summary": item.get("summary", item.get("intro", "")),
                        "source": "新浪财经",
                        "url": item.get("url", "") or item.get("link", ""),
                        "pub_time": pub_dt.strftime("%Y-%m-%d %H:%M"),
                        "timestamp": pub_dt.timestamp(),
                    })
                if results:
                    return results
    except Exception as e:
        print(f"[调试] 新浪JSON接口失败: {e}", flush=True)

    try:
        html_url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol=sh{stock_code}.phtml"
        resp = requests.get(html_url, headers=headers, timeout=10, proxies=proxies)
        resp.encoding = "gb2312"
        html = resp.text

        pattern = r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>.*?>(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
        matches = re.findall(pattern, html, re.DOTALL)
        results.clear()
        for url_href, title, pub_str in matches:
            if not title.strip():
                continue
            pub_dt = datetime.strptime(pub_str, "%Y-%m-%d %H:%M")
            pub_dt = pub_dt.replace(tzinfo=CST)
            if url_href.startswith("//"):
                url_href = "https:" + url_href
            elif url_href.startswith("/"):
                url_href = "https://finance.sina.com.cn" + url_href
            results.append({
                "title": title.strip(),
                "summary": "",
                "source": "新浪财经",
                "url": url_href,
                "pub_time": pub_dt.strftime("%Y-%m-%d %H:%M"),
                "timestamp": pub_dt.timestamp(),
            })
    except Exception as e:
        print(f"[警告] 新浪财经HTML抓取失败: {e}", flush=True)

    return results


def fetch_stock_price(stock_code="603296"):
    """获取实时股票行情"""
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"1.{stock_code}",
        "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f169,f170,f100"
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://quote.eastmoney.com/",
    }
    proxies = {"http": None, "https": None}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10, proxies=proxies)
        data = resp.json()
        d = data.get("data", {})
        if d:
            def format_num(val):
                if val is None:
                    return "--"
                try:
                    return f"{val:.2f}"
                except:
                    return str(val)

            def format_market_cap(val):
                if val is None:
                    return "--"
                try:
                    return f"{val / 100000000:.2f}"
                except:
                    return "--"

            change_pct = d.get("f48", 0)
            change_pct_str = f"{change_pct:+.2f}%" if change_pct is not None else "--"
            return {
                "name": d.get("f58", stock_code),
                "code": d.get("f57", stock_code),
                "price": format_num(d.get("f43")),
                "high": format_num(d.get("f44")),
                "low": format_num(d.get("f45")),
                "open": format_num(d.get("f46")),
                "change": format_num(d.get("f47")),
                "change_pct": change_pct_str,
                "total_market_cap": format_market_cap(d.get("f169")),
                "circulating_market_cap": format_market_cap(d.get("f170")),
            }
    except Exception as e:
        print(f"[警告] 股票行情获取失败: {e}", flush=True)
    return None


def deduplicate_news(news_list):
    """去重（按标题相似度）"""
    seen = set()
    unique = []
    for item in news_list:
        key = item["title"][:20].strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def fetch_all_news(stock_code="603296", hours_back=24, max_count=20):
    """从所有源抓取新闻并合并去重"""
    all_news = []
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            em_future = executor.submit(fetch_eastmoney_news, stock_code, max_count)
            sina_future = executor.submit(fetch_sina_news, stock_code)
            all_news.extend(em_future.result())
            all_news.extend(sina_future.result())
    except Exception as e:
        print(f"[警告] 并行抓取失败，切换为串行: {e}", flush=True)
        all_news.extend(fetch_eastmoney_news(stock_code, max_count))
        all_news.extend(fetch_sina_news(stock_code))

    all_news = deduplicate_news(all_news)
    all_news.sort(key=lambda x: x["timestamp"], reverse=True)

    cutoff = time.time() - hours_back * 3600
    filtered = [n for n in all_news if n["timestamp"] >= cutoff]
    return filtered[:max_count]


def format_news_summary(news_list, stock_price=None, stock_name="华勤技术"):
    """格式化新闻摘要文本"""
    today = datetime.now(CST).strftime("%Y年%m月%d日")
    lines = []
    lines.append(f"📊 {stock_name}（{today}）新闻汇总")
    lines.append("")
    if stock_price:
        lines.append(f"💰 股价: {stock_price['price']} 元")
        lines.append(f"📈 涨跌幅: {stock_price['change_pct']}")
        lines.append(f"📉 今日区间: {stock_price['low']} ~ {stock_price['high']}")
        lines.append(f"🏢 总市值: {stock_price['total_market_cap']} 亿")
        lines.append("")
    if not news_list:
        lines.append("最近24小时暂无相关新闻。")
        return "\n".join(lines)
    lines.append(f"📰 共 {len(news_list)} 条相关新闻：")
    lines.append("")
    for i, item in enumerate(news_list, 1):
        lines.append(f"{i}. [{item['source']}] {item['title']}")
        if item.get("summary"):
            summary = item["summary"]
            if len(summary) > 100:
                summary = summary[:100] + "..."
            lines.append(f"   {summary}")
        lines.append(f"   发布时间: {item['pub_time']}")
        lines.append(f"   链接: {item['url']}")
        lines.append("")
    lines.append("---")
    lines.append("🤖 数据来源: 东方财富 & 新浪财经")
    return "\n".join(lines)
