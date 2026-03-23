import feedparser
import os
import time
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlunparse
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 尼龙胶板专用 RSS 源 =====
RSS_URLS = [
    # 1. Google News 搜索：尼龙胶板相关的供应商、厂家、行业动态
    "https://news.google.com/rss/search?q=%E5%B0%BC%E9%BE%99%E8%83%B6%E6%9D%BF+%E4%BE%9B%E5%BA%94%E5%95%86+OR+%E5%B0%BC%E9%BE%99%E6%9D%BF+%E5%8E%82%E5%AE%B6+OR+%E5%B0%BC%E9%BE%99%E5%A4%8D%E5%90%88%E6%9D%90%E6%96%99+%E4%BC%81%E4%B8%9A+OR+PA6+%E6%9D%BF%E6%9D%90+%E4%BE%9B%E5%BA%94%E5%95%86&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 2. 社交媒体 RSSHub 搜索（抖音、B站、微博）
    "https://rsshub.app/douyin/search/尼龙胶板",
    "https://rsshub.app/bilibili/vsearch/尼龙胶板",
    "https://rsshub.app/weibo/search/尼龙胶板",
]

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def normalize_url(url):
    """标准化URL：去除常见追踪参数，并统一为小写"""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid']
        filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        new_query = '&'.join([f"{k}={v[0]}" for k, v in filtered_params.items()])
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed).rstrip('/').lower()
    except:
        return url.rstrip('/').lower()

def send_feishu_message(text):
    webhook_url = os.getenv("FEISHU_WEBHOOK")
    if not webhook_url:
        print("❌ 环境变量 FEISHU_WEBHOOK 未设置")
        return
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 200:
            print("✅ 飞书消息发送成功")
        else:
            print(f"❌ 飞书消息发送失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ 飞书请求异常: {e}")

def should_keep_article(title, content):
    """必须包含尼龙胶板相关关键词，且不含黑名单词"""
    if not title and not content:
        return False

    text = (title + " " + content).lower()

    # 强相关词（必须有至少一个）
    strong_keywords = [
        "尼龙胶板", "尼龙板", "pa6", "pa66", "工程塑料", "塑料板材",
        "供应商", "厂家", "生产厂家", "制造", "加工", "批发",
        "复合材料", "绝缘板", "耐磨板", "塑胶材料"
    ]
    if not any(kw in text for kw in strong_keywords):
        return False

    # 黑名单词（出现则丢弃）
    blacklist = [
        "手机", "汽车", "锂矿", "锂电", "小红书", "电商", "抖音", "快手",
        "微信", "支付宝", "外卖", "打车", "游戏", "影视", "股票", "基金",
        "理财", "房价", "地产", "消费", "零售", "演唱会"
    ]
    if any(bw in text for bw in blacklist):
        return False

    return True

def get_new_feed_items_from(feed_url):
    print(f"正在抓取 RSS: {feed_url}")
    try:
        rss = feedparser.parse(feed_url)
        print(f"RSS 解析成功，条目总数: {len(rss.entries)}")
    except Exception as e:
        print(f"Error parsing feed {feed_url}: {e}")
        return []

    current_time_struct = rss.get("updated_parsed") or rss.get("published_parsed")
    current_time = _parse_struct_time_to_timestamp(current_time_struct) if current_time_struct else time.time()

    new_items = []
    for item in rss.entries:
        pub_date = item.get("published_parsed") or item.get("updated_parsed")
        if not pub_date:
            continue

        blog_published_time = _parse_struct_time_to_timestamp(pub_date)
        diff = time_difference(current_time, blog_published_time)
        if diff["diffInSeconds"] >= RUN_FREQUENCY:
            continue

        title = item.get("title", "")
        content = item.get("summary", "") or item.get("description", "")

        if not should_keep_article(title, content):
            continue

        new_items.append({
            "title": title,
            "link": item.get("link", ""),
            "content": content,
            "published_parsed": pub_date
        })

    print(f"本次抓取到 {len(new_items)} 条新文章")
    return new_items

def get_new_feed_items():
    # 加载已推送链接缓存（保存7天）
    cache_file = "/tmp/pushed_links_cache_nylon.json"
    pushed_links = set()
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                cutoff_time = datetime.now() - timedelta(days=7)
                for link, timestamp_str in data.items():
                    try:
                        if datetime.fromisoformat(timestamp_str) > cutoff_time:
                            pushed_links.add(link)
                    except:
                        pass
    except Exception as e:
        print(f"⚠️ 读取推送缓存失败: {e}")

    # 抓取所有源的新文章
    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    print(f"总共 {len(all_new_feed_items)} 条新文章待处理（抓取总数）")

    # 单次运行内去重
    unique_items_dict = {}
    for item in all_new_feed_items:
        normalized_link = normalize_url(item['link'])
        if normalized_link not in unique_items_dict:
            unique_items_dict[normalized_link] = item

    print(f"单次运行内去重后剩余 {len(unique_items_dict)} 条")

    # 跨周期去重
    truly_new_items = []
    for item in unique_items_dict.values():
        normalized_link = normalize_url(item['link'])
        if normalized_link not in pushed_links:
            truly_new_items.append(item)

    print(f"跨周期去重后剩余 {len(truly_new_items)} 条新文章待推送")

    # 推送并更新缓存
    for item in truly_new_items:
        text = f"{item['title']}\n{item['link']}"
        send_feishu_message(text)
        pushed_links.add(normalize_url(item['link']))

    # 保存更新后的缓存
    try:
        data_to_save = {link: datetime.now().isoformat() for link in pushed_links}
        with open(cache_file, 'w') as f:
            json.dump(data_to_save, f)
    except Exception as e:
        print(f"⚠️ 保存推送缓存失败: {e}")

    return truly_new_items
