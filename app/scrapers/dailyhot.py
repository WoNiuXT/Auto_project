"""DailyHotApi 热点采集客户端。

职责：
- 调用 DailyHotApi REST API 获取多平台热搜
- 按热度排序、关键词过滤、去重
- 输出：[{title, source, hot_score, url, description}, ...]
"""
import json
import urllib.request
import urllib.error
from typing import List, Dict, Optional


class DailyHotScraper:
    """DailyHotApi 热点采集器。"""

    def __init__(self, base_url: str = "http://127.0.0.1:6688",
                 platforms: list = None, max_topics: int = 5,
                 exclude_keywords: list = None):
        self.base_url = base_url.rstrip("/")
        self.platforms = platforms or ["weibo", "zhihu", "bilibili", "douyin"]
        self.max_topics = max_topics
        self.exclude_keywords = exclude_keywords or []

    def fetch_platform(self, platform: str) -> List[Dict]:
        """获取单个平台的热搜列表。"""
        url = f"{self.base_url}/{platform}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # DailyHotApi 返回格式可能是 list 或 dict with "data" key
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
                return []
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
            print(f"  [WARN] {platform} 采集失败: {e}")
            return []

    def fetch_all(self) -> List[Dict]:
        """采集所有平台热搜，去重 + 过滤 + 排序。"""
        all_topics = []
        seen_titles = set()

        for platform in self.platforms:
            raw = self.fetch_platform(platform)
            for item in raw:
                title = item.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                # 关键词过滤
                if any(kw in title for kw in self.exclude_keywords):
                    continue
                seen_titles.add(title)
                all_topics.append({
                    "title": title,
                    "source": platform,
                    "hot_score": item.get("hot", 0) or 0,
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                })

        # 按热度排序，取 top N
        all_topics.sort(key=lambda x: x["hot_score"], reverse=True)
        return all_topics[:self.max_topics]