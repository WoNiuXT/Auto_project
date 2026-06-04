"""多平台发布器。
职责:
- 加载各平台 Cookie
- 按平台适配器模式发布（图片 + 文案 + 话题标签）
- 频率限制（平台间间隔 >= 30s）
- 发布结果记录
- Cookie 有效性预检查

支持平台:
- bilibili (B站图文动态)
- douyin (抖音图文)
- xhs (小红书图文笔记)
"""
import json
import os
import time
import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse
import uuid
import hashlib
from typing import Dict, List, Optional
from datetime import datetime


# 平台配置
PLATFORM_CONFIG = {
    "douyin": {
        "name": "抖音",
        "cookie_file": "douyin.json",
        "check_url": "https://creator.douyin.com/creator-micro/home",
        "upload_url": "https://creator.douyin.com/web/api/media/upload",
        "publish_url": "https://creator.douyin.com/web/api/publish",
    },
    "bilibili": {
        "name": "B站",
        "cookie_file": "bilibili.json",
        "check_url": "https://member.bilibili.com/platform/home",
        "upload_url": "https://api.bilibili.com/x/dynamic/feed/draw/upload",
        "publish_url": "https://api.bilibili.com/x/dynamic/feed/create",
    },
    "xhs": {
        "name": "小红书",
        "cookie_file": "xhs.json",
        "check_url": "https://creator.xiaohongshu.com/creator/home",
        "upload_url": "https://creator.xiaohongshu.com/api/upload",
        "publish_url": "https://creator.xiaohongshu.com/api/publish",
    },
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class Publisher:
    """多平台发布器。"""

    def __init__(self, cookies_dir: str = "cookies",
                 interval_seconds: int = 30,
                 max_per_hour: int = 5):
        self.cookies_dir = cookies_dir
        self.interval_seconds = interval_seconds
        self.max_per_hour = max_per_hour
        self._publish_log: List[Dict] = []

    # ─── Cookie 管理 ──────────────────────────────────────

    def _load_cookies(self, platform: str) -> Optional[http.cookiejar.CookieJar]:
        """加载指定平台的 Cookie。"""
        config = PLATFORM_CONFIG.get(platform)
        if not config:
            return None
        cookie_path = os.path.join(self.cookies_dir, config["cookie_file"])
        if not os.path.isfile(cookie_path):
            return None

        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

        cj = http.cookiejar.CookieJar()
        if isinstance(cookies_data, list):
            for c in cookies_data:
                cookie = http.cookiejar.Cookie(
                    version=0, name=c.get("name", ""), value=c.get("value", ""),
                    port=None, port_specified=False,
                    domain=c.get("domain", ""), domain_specified=bool(c.get("domain")),
                    domain_initial_dot=c.get("domain", "").startswith("."),
                    path=c.get("path", "/"), path_specified=bool(c.get("path")),
                    secure=c.get("secure", False), expires=c.get("expires"),
                    discard=False, comment=None, comment_url=None, rest={}, rfc2109=False,
                )
                cj.set_cookie(cookie)
        elif isinstance(cookies_data, dict):
            for name, value in cookies_data.items():
                cookie = http.cookiejar.Cookie(
                    version=0, name=name, value=str(value),
                    port=None, port_specified=False,
                    domain="", domain_specified=False, domain_initial_dot=False,
                    path="/", path_specified=False,
                    secure=False, expires=None,
                    discard=False, comment=None, comment_url=None, rest={}, rfc2109=False,
                )
                cj.set_cookie(cookie)
        return cj

    def _build_opener(self, platform: str) -> Optional[urllib.request.OpenerDirector]:
        """构建带 Cookie 的 URL opener。"""
        cj = self._load_cookies(platform)
        if not cj:
            return None
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj)
        )
        opener.addheaders = [("User-Agent", USER_AGENT)]
        return opener

    def check_cookie(self, platform: str) -> tuple:
        """检查指定平台 Cookie 是否有效。
        Returns:
            (valid: bool, message: str)
        """
        config = PLATFORM_CONFIG.get(platform)
        if not config:
            return False, f"未知平台: {platform}"

        opener = self._build_opener(platform)
        if not opener:
            return False, f"Cookie 文件不存在: {config['cookie_file']}"

        try:
            resp = opener.open(config["check_url"], timeout=10)
            status = resp.getcode()
            body = resp.read(2048).decode("utf-8", errors="replace")
            resp.close()
            if status == 200 and "login" not in body.lower()[:500]:
                return True, f"有效 (HTTP {status})"
            return False, f"可能已失效 (HTTP {status})"
        except urllib.error.HTTPError as e:
            return False, f"已失效 (HTTP {e.code})"
        except Exception as e:
            return False, f"检查失败: {e}"

    def check_all(self, platforms: List[str]) -> Dict[str, tuple]:
        """检查所有平台 Cookie 状态。"""
        results = {}
        for p in platforms:
            results[p] = self.check_cookie(p)
        return results

    # ─── 图片上传 ────────────────────────────────────────

    def _upload_image_bilibili(self, opener: urllib.request.OpenerDirector,
                               image_path: str) -> Optional[Dict]:
        """上传图片到 B站，返回图片信息。"""
        if not os.path.isfile(image_path):
            print(f"    [ERROR] 图片不存在: {image_path}")
            return None

        boundary = uuid.uuid4().hex
        filename = os.path.basename(image_path)

        with open(image_path, "rb") as f:
            file_data = f.read()

        # 构建 multipart/form-data
        body = b""
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="file_up"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: image/png\r\n\r\n"
        body += file_data
        body += f"\r\n--{boundary}--\r\n".encode()

        url = "https://api.bilibili.com/x/dynamic/feed/draw/upload"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Referer", "https://t.bilibili.com/")

        try:
            with opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 0:
                    img_data = data.get("data", {})
                    print(f"    [OK] B站图片上传成功")
                    return img_data
                else:
                    print(f"    [ERROR] B站图片上传失败: {data.get('message', '未知错误')}")
                    return None
        except Exception as e:
            print(f"    [ERROR] B站图片上传异常: {e}")
            return None

    def _upload_image_douyin(self, opener: urllib.request.OpenerDirector,
                             image_path: str) -> Optional[str]:
        """上传图片到抖音，返回 image_uri。"""
        if not os.path.isfile(image_path):
            print(f"    [ERROR] 图片不存在: {image_path}")
            return None

        boundary = uuid.uuid4().hex
        filename = os.path.basename(image_path)

        with open(image_path, "rb") as f:
            file_data = f.read()

        body = b""
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: image/png\r\n\r\n"
        body += file_data
        body += f"\r\n--{boundary}--\r\n".encode()

        url = "https://creator.douyin.com/web/api/media/upload"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Referer", "https://creator.douyin.com/")

        try:
            with opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status_code") == 0:
                    uri = data.get("data", {}).get("image_uri", "")
                    print(f"    [OK] 抖音图片上传成功")
                    return uri
                else:
                    print(f"    [ERROR] 抖音图片上传失败: {data}")
                    return None
        except Exception as e:
            print(f"    [ERROR] 抖音图片上传异常: {e}")
            return None

    def _upload_image_xhs(self, opener: urllib.request.OpenerDirector,
                           image_path: str) -> Optional[str]:
        """上传图片到小红书，返回 image_id。"""
        if not os.path.isfile(image_path):
            print(f"    [ERROR] 图片不存在: {image_path}")
            return None

        boundary = uuid.uuid4().hex
        filename = os.path.basename(image_path)

        with open(image_path, "rb") as f:
            file_data = f.read()

        body = b""
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: image/png\r\n\r\n"
        body += file_data
        body += f"\r\n--{boundary}--\r\n".encode()

        url = "https://creator.xiaohongshu.com/api/upload"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Referer", "https://creator.xiaohongshu.com/")

        try:
            with opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    img_id = data.get("data", {}).get("file_id", "")
                    print(f"    [OK] 小红书图片上传成功")
                    return img_id
                else:
                    print(f"    [ERROR] 小红书图片上传失败: {data}")
                    return None
        except Exception as e:
            print(f"    [ERROR] 小红书图片上传异常: {e}")
            return None

    # ─── 内容发布 ────────────────────────────────────────

    def _publish_bilibili(self, opener: urllib.request.OpenerDirector,
                          images: List[str], caption: str,
                          hashtags: List[str] = None) -> Dict:
        """发布图文动态到 B站。"""
        # 1. 上传图片
        uploaded_images = []
        for img_path in images[:9]:  # B站最多9张图
            img_info = self._upload_image_bilibili(opener, img_path)
            if img_info:
                uploaded_images.append(img_info)

        if not uploaded_images:
            return {"status": "failed", "publish_url": "", "error": "图片上传全部失败"}

        # 2. 构建发布请求
        tags = hashtags or []
        topic_str = " ".join(f"#{t}" for t in tags) if tags else ""
        full_text = f"{caption}\n{topic_str}".strip()

        # B站图文动态发布
        post_data = {
            "dyn_req": {
                "content": full_text,
                "pics": [
                    {
                        "img_src": img.get("image_url", img.get("img_src", "")),
                        "img_width": img.get("img_width", 1024),
                        "img_height": img.get("img_height", 1024),
                    }
                    for img in uploaded_images
                ],
                "ctrl": [],
                "from": "create",
                "platform": 3,
            }
        }

        payload = json.dumps(post_data).encode("utf-8")
        url = "https://api.bilibili.com/x/dynamic/feed/create"
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Referer", "https://t.bilibili.com/")

        try:
            with opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 0:
                    dyn_id = data.get("data", {}).get("dyn_id", "")
                    publish_url = f"https://t.bilibili.com/{dyn_id}" if dyn_id else ""
                    return {"status": "success", "publish_url": publish_url, "error": ""}
                else:
                    return {"status": "failed", "publish_url": "",
                            "error": f"B站发布失败: {data.get('message', '')}"}
        except Exception as e:
            return {"status": "failed", "publish_url": "", "error": f"B站发布异常: {e}"}

    def _publish_douyin(self, opener: urllib.request.OpenerDirector,
                        images: List[str], caption: str,
                        hashtags: List[str] = None) -> Dict:
        """发布图文到抖音。"""
        # 1. 上传图片
        uploaded_uris = []
        for img_path in images[:12]:  # 抖音最多12张图
            uri = self._upload_image_douyin(opener, img_path)
            if uri:
                uploaded_uris.append(uri)

        if not uploaded_uris:
            return {"status": "failed", "publish_url": "", "error": "图片上传全部失败"}

        # 2. 发布
        tags = hashtags or []
        post_data = {
            "post_type": "image",
            "title": caption[:30],
            "content": caption,
            "image_uri_list": uploaded_uris,
            "cover_image_uri": uploaded_uris[0],
            "tags": tags,
        }

        payload = json.dumps(post_data).encode("utf-8")
        url = "https://creator.douyin.com/web/api/publish"
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Referer", "https://creator.douyin.com/")

        try:
            with opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status_code") == 0:
                    item_id = data.get("data", {}).get("item_id", "")
                    publish_url = f"https://www.douyin.com/video/{item_id}" if item_id else ""
                    return {"status": "success", "publish_url": publish_url, "error": ""}
                else:
                    return {"status": "failed", "publish_url": "",
                            "error": f"抖音发布失败: {data}"}
        except Exception as e:
            return {"status": "failed", "publish_url": "", "error": f"抖音发布异常: {e}"}

    def _publish_xhs(self, opener: urllib.request.OpenerDirector,
                     images: List[str], caption: str,
                     hashtags: List[str] = None) -> Dict:
        """发布图文笔记到小红书。"""
        # 1. 上传图片
        uploaded_ids = []
        for img_path in images[:9]:  # 小红书最多9张图
            img_id = self._upload_image_xhs(opener, img_path)
            if img_id:
                uploaded_ids.append(img_id)

        if not uploaded_ids:
            return {"status": "failed", "publish_url": "", "error": "图片上传全部失败"}

        # 2. 发布
        tags = hashtags or []
        post_data = {
            "title": caption[:20],
            "desc": caption,
            "image_ids": uploaded_ids,
            "tags": [{"name": t} for t in tags],
            "post_type": "normal",
        }

        payload = json.dumps(post_data).encode("utf-8")
        url = "https://creator.xiaohongshu.com/api/publish"
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Referer", "https://creator.xiaohongshu.com/")

        try:
            with opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    note_id = data.get("data", {}).get("note_id", "")
                    publish_url = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""
                    return {"status": "success", "publish_url": publish_url, "error": ""}
                else:
                    return {"status": "failed", "publish_url": "",
                            "error": f"小红书发布失败: {data}"}
        except Exception as e:
            return {"status": "failed", "publish_url": "", "error": f"小红书发布异常: {e}"}

    # ─── 公共发布接口 ────────────────────────────────────

    def publish(self, platform: str, images: List[str], caption: str,
                hashtags: List[str] = None) -> Dict:
        """发布内容到指定平台。
        Args:
            platform: 平台名（douyin/bilibili/xhs）
            images: 图片文件路径列表
            caption: 发布文案
            hashtags: 话题标签列表

        Returns:
            {status: "success"/"failed", publish_url: "", error: ""}
        """
        config = PLATFORM_CONFIG.get(platform)
        if not config:
            return {"status": "failed", "publish_url": "", "error": f"未知平台: {platform}"}

        # 检查 Cookie
        valid, msg = self.check_cookie(platform)
        if not valid:
            return {"status": "failed", "publish_url": "", "error": f"Cookie 无效: {msg}"}

        # 构建 opener
        opener = self._build_opener(platform)
        if not opener:
            return {"status": "failed", "publish_url": "", "error": "无法构建 opener"}

        print(f"  [{config['name']}] 发布 {len(images)} 张图片...")
        print(f"  [{config['name']}] 文案: {caption[:50]}...")

        # 分平台发布
        if platform == "bilibili":
            result = self._publish_bilibili(opener, images, caption, hashtags)
        elif platform == "douyin":
            result = self._publish_douyin(opener, images, caption, hashtags)
        elif platform == "xhs":
            result = self._publish_xhs(opener, images, caption, hashtags)
        else:
            result = {"status": "failed", "publish_url": "",
                      "error": f"平台 {platform} 暂未实现"}

        # 记录发布日志
        log_entry = {
            "platform": platform,
            "platform_name": config["name"],
            "status": result["status"],
            "publish_url": result.get("publish_url", ""),
            "error": result.get("error", ""),
            "image_count": len(images),
            "caption_preview": caption[:50],
            "timestamp": datetime.now().isoformat(),
        }
        self._publish_log.append(log_entry)

        if result["status"] == "success":
            print(f"  [{config['name']}] 发布成功! {result.get('publish_url', '')}")
        else:
            print(f"  [{config['name']}] 发布失败: {result.get('error', '')}")

        return result

    def publish_all(self, platforms: List[str], images: List[str],
                    caption: str, hashtags: List[str] = None) -> List[Dict]:
        """发布到多个平台（带频率限制）。
        Returns:
            [{platform, status, publish_url, error}, ...]
        """
        results = []
        for i, platform in enumerate(platforms):
            if i > 0:
                print(f"  等待 {self.interval_seconds}s...")
                time.sleep(self.interval_seconds)

            result = self.publish(platform, images, caption, hashtags)
            result["platform"] = platform
            results.append(result)

        return results

    def get_publish_log(self) -> List[Dict]:
        """获取本次会话的发布日志。"""
        return self._publish_log

    def save_publish_log(self, filepath: str):
        """保存发布日志到文件。"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._publish_log, f, ensure_ascii=False, indent=2)