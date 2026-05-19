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


def fetch_eastmoney_news(stock_code="603296", stock_name="华勤技术", page_size=20):
    """从东方财富获取个股新闻（尝试多个接口 + HTML抓取兜底）"""
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

    keyword_param = {
        "uid": "",
        "keyword": stock_name,
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
        {"url": "https://search-api-web.eastmoney.com/search/jsonp", "params": {"cb": "", "param": json.dumps(keyword_param)}},
        {"url": "https://push.eastmoney.com/api/qt/article/list", "params": {"secuCode": stock_code, "secuMarket": "1", "pageNum": 1, "pageSize": page_size}},
    ]

    for api in apis:
        try:
            resp = requests.get(api["url"], params=api["params"], headers=headers, timeout=10, proxies=proxies)
            text = resp.text.strip()
            if not text:
                continue
            if not text.startswith("{"):
                match = re.search(r'\(([\s\S]+)\)\s*$', text)
                if match:
                    text = match.group(1)
            parsed = json.loads(text)
            articles = extract_articles_from_response(parsed)
            if articles:
                print(f"[调试] 东方财富接口 {api['url'].split('/')[-1]} 获取到 {len(articles)} 条新闻", flush=True)
                return parse_article_list(articles, "东方财富")
        except Exception as e:
            print(f"[调试] 东方财富接口 {api['url']} 失败: {e}", flush=True)
            continue

    print(f"[调试] 东方财富接口均返回空，尝试HTML抓取兜底...", flush=True)
    return fetch_eastmoney_news_html(stock_code, page_size)


def extract_articles_from_response(data):
    """从各种API响应结构中提取文章列表"""
    if not data:
        return None
    if isinstance(data, list):
        return data
    for key in ["list", "data", "result", "articles"]:
        val = data.get(key)
        if isinstance(val, list):
            if val:
                return val
    if isinstance(data.get("data"), dict):
        for sub in ["list", "articles", "result"]:
            val = data["data"].get(sub)
            if isinstance(val, list):
                if val:
                    return val
    if isinstance(data.get("result"), dict):
        for sub in ["list", "data", "articles"]:
            val = data["result"].get(sub)
            if isinstance(val, list):
                if val:
                    return val
    return None


def parse_article_list(articles, source):
    """解析文章列表为统一格式"""
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
            "source": source,
            "url": art_url,
            "pub_time": pub_dt.strftime("%Y-%m-%d %H:%M"),
            "timestamp": pub_dt.timestamp(),
        })
    return results


def fetch_eastmoney_news_html(stock_code="603296", page_size=20):
    """通过抓取东方财富股吧HTML页面获取新闻"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://guba.eastmoney.com/",
    }
    proxies = {"http": None, "https": None}
    results = []

    urls = [
        f"https://guba.eastmoney.com/list,{stock_code}.html",
        f"https://so.eastmoney.com/news/s?keyword={stock_code}&pageindex=1&pagesize={page_size}",
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            resp.encoding = "utf-8"
            html = resp.text
            titles = re.findall(r'title="([^"]*)"', html)
            links = re.findall(r'href="(https?://[^"]*)"', html)
            if titles and links:
                for i, title in enumerate(titles):
                    if stock_code in title:
                        results.append({
                            "title": title,
                            "summary": "",
                            "source": "东方财富",
                            "url": links[i] if i < len(links) else "",
                            "pub_time": datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
                            "timestamp": time.time(),
                        })
                if results:
                    return results[:page_size]
        except Exception as e:
            print(f"[调试] 东方财富HTML抓取失败: {e}", flush=True)
            continue

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


def fetch_baidu_news(keyword="华勤技术", page_size=20):
    """通过百度新闻搜索获取新闻作为兜底"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    proxies = {"http": None, "https": None}
    results = []
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                f"https://news.baidu.com/ns?word={urllib.parse.quote(keyword)}&pn=0&rn={page_size}&ct=1&tn=news&ie=utf-8&bt=0&et=0",
                headers=headers, timeout=15, proxies=proxies
            )
            resp.encoding = "utf-8"
            html = resp.text
            items = re.findall(r'<h3[^>]*>.*?<a\s+href="([^"]+)"[^>]*>(.*?)</a>.*?</h3>', html, re.DOTALL)
            if not items:
                items = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
                if items:
                    items = [(u, t) for u, t in items if keyword in u or keyword in t]
            for url, title_html in items:
                title = re.sub(r'<[^>]+>', '', title_html).strip()
                if not title:
                    continue
                results.append({
                    "title": title,
                    "summary": "",
                    "source": "百度新闻",
                    "url": url,
                    "pub_time": datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
                    "timestamp": time.time(),
                })
            if results:
                break
        except Exception as e:
            print(f"[调试] 百度新闻抓取失败(第{attempt+1}次): {e}", flush=True)
            time.sleep(1)
    return results[:page_size]


def fetch_stock_price_sina(stock_code="603296"):
    """通过新浪财经获取实时股票行情"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/",
    }
    proxies = {"http": None, "https": None}
    try:
        resp = requests.get(f"https://hq.sinajs.cn/list=sh{stock_code}", headers=headers, timeout=10, proxies=proxies)
        resp.encoding = "gbk"
        text = resp.text.strip()
        if "hq_str_" not in text:
            return None
        parts = text.split('"')[1].split(",")
        if len(parts) < 32:
            return None
        price = float(parts[3]) if parts[3] else 0
        if price <= 0 or price > 10000:
            return None
        prev_close = float(parts[2]) if parts[2] else price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        return {
            "name": parts[0] if parts[0] else stock_code,
            "code": stock_code,
            "price": f"{price:.2f}",
            "high": f"{float(parts[4]):.2f}" if parts[4] else "--",
            "low": f"{float(parts[5]):.2f}" if parts[5] else "--",
            "open": f"{float(parts[1]):.2f}" if parts[1] else "--",
            "change": f"{change:.2f}",
            "change_pct": f"{change_pct:+.2f}%",
            "total_market_cap": "--",
            "circulating_market_cap": "--",
        }
    except Exception as e:
        print(f"[调试] 新浪行情接口失败: {e}", flush=True)
    return None


def fetch_stock_price(stock_code="603296"):
    """获取实时股票行情（新浪 -> 东方财富兜底）"""
    result = fetch_stock_price_sina(stock_code)
    if result:
        print(f"[调试] 新浪行情获取成功: {result['price']} 元", flush=True)
        return result

    urls = [
        {"url": "https://push2.eastmoney.com/api/qt/stock/get", "params": {"secid": f"1.{stock_code}", "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f169,f170,f100"}},
        {"url": "https://push2.eastmoney.com/api/qt/stock/get", "params": {"secid": f"0.{stock_code}", "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f169,f170,f100"}},
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    proxies = {"http": None, "https": None}

    for api in urls:
        try:
            resp = requests.get(api["url"], params=api["params"], headers=headers, timeout=10, proxies=proxies)
            data = resp.json()
            d = data.get("data", {})
            if d and d.get("f43") and d.get("f43") != "-":
                price = float(d["f43"])
                if price <= 0 or price > 10000:
                    print(f"[调试] 股价 {price} 超出合理范围，跳过此接口", flush=True)
                    continue

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

                change_pct = d.get("f48")
                if change_pct is not None and abs(change_pct) < 100:
                    change_pct_str = f"{change_pct:+.2f}%"
                else:
                    change_pct_str = "--"

                return {
                    "name": d.get("f58", stock_code),
                    "code": d.get("f57", stock_code),
                    "price": format_num(price),
                    "high": format_num(d.get("f44")),
                    "low": format_num(d.get("f45")),
                    "open": format_num(d.get("f46")),
                    "change": format_num(d.get("f47")),
                    "change_pct": change_pct_str,
                    "total_market_cap": format_market_cap(d.get("f169")),
                    "circulating_market_cap": format_market_cap(d.get("f170")),
                }
        except Exception as e:
            print(f"[调试] 东方财富行情接口 {api['url']} 失败: {e}", flush=True)
            continue

    print(f"[警告] 股票行情获取失败", flush=True)
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


def fetch_all_news(stock_code="603296", stock_name="华勤技术", hours_back=24, max_count=20):
    """从所有源抓取新闻并合并去重"""
    all_news = []
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            em_future = executor.submit(fetch_eastmoney_news, stock_code, stock_name, max_count)
            sina_future = executor.submit(fetch_sina_news, stock_code)
            baidu_future = executor.submit(fetch_baidu_news, stock_name, max_count)
            all_news.extend(em_future.result())
            all_news.extend(sina_future.result())
            all_news.extend(baidu_future.result())
    except Exception as e:
        print(f"[警告] 并行抓取失败，切换为串行: {e}", flush=True)
        all_news.extend(fetch_eastmoney_news(stock_code, stock_name, max_count))
        all_news.extend(fetch_sina_news(stock_code))
        all_news.extend(fetch_baidu_news(stock_name, max_count))

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
