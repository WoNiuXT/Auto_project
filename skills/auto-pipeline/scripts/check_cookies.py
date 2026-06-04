#!/usr/bin/env python3
"""检查各平台 Cookie 有效性（通过 HTTP 请求验证）。"""
import sys
import os
import json
import argparse
import urllib.request
import urllib.error
import http.cookiejar


COOKIES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies")

PLATFORMS = {
    "douyin": {
        "name": "抖音",
        "check_url": "https://creator.douyin.com/creator-micro/home",
        "cookie_file": "douyin.json",
    },
    "bilibili": {
        "name": "B站",
        "check_url": "https://member.bilibili.com/platform/home",
        "cookie_file": "bilibili.json",
    },
    "xhs": {
        "name": "小红书",
        "check_url": "https://creator.xiaohongshu.com/creator/home",
        "cookie_file": "xhs.json",
    },
}


def load_cookies(platform):
    """加载指定平台的 Cookie 文件。"""
    info = PLATFORMS.get(platform)
    if not info:
        return None
    cookie_path = os.path.join(COOKIES_DIR, info["cookie_file"])
    if not os.path.isfile(cookie_path):
        return None
    try:
        with open(cookie_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def check_cookie_valid(platform):
    """通过 HTTP 请求验证 Cookie 是否有效。"""
    info = PLATFORMS.get(platform)
    if not info:
        return False, "未知平台"

    cookies_data = load_cookies(platform)
    if cookies_data is None:
        return False, "Cookie 文件不存在或格式错误"
    if isinstance(cookies_data, (dict, list)) and len(cookies_data) == 0:
        return False, "Cookie 文件为空"

    # 构建 cookie jar
    cj = http.cookiejar.CookieJar()
    if isinstance(cookies_data, list):
        # 格式: [{"name": "xxx", "value": "yyy", "domain": ".example.com"}, ...]
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
        # 格式: {"cookie_name": "cookie_value", ...}
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

    # 发起请求验证
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")]
    try:
        resp = opener.open(info["check_url"], timeout=10)
        status = resp.getcode()
        body = resp.read(1024).decode("utf-8", errors="replace")
        resp.close()

        # 判断是否被重定向到登录页
        if status == 200 and "login" not in body.lower()[:500]:
            return True, f"有效 (HTTP {status})"
        else:
            return False, f"可能已失效 (HTTP {status}, 页面含 login 关键词)"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, f"已失效 (HTTP {e.code})"
        return False, f"请求失败 (HTTP {e.code})"
    except Exception as e:
        return False, f"请求异常: {e}"


def main():
    parser = argparse.ArgumentParser(description="检查各平台 Cookie 有效性")
    parser.add_argument("--platform", "-p", help="指定平台 (douyin/bilibili/xhs)")
    parser.add_argument("--cookies-dir", help="Cookie 目录路径")
    args = parser.parse_args()

    global COOKIES_DIR
    if args.cookies_dir:
        COOKIES_DIR = args.cookies_dir

    print("=== Cookie 状态检查 ===\n")

    platforms_to_check = [args.platform] if args.platform else list(PLATFORMS.keys())

    all_ok = True
    for platform in platforms_to_check:
        info = PLATFORMS.get(platform)
        if not info:
            print(f"[SKIP] 未知平台: {platform}")
            continue

        print(f"检查 {info['name']} ({platform})...")
        valid, msg = check_cookie_valid(platform)
        if valid:
            print(f"  [OK] {msg}")
        else:
            print(f"  [FAIL] {msg}")
            print(f"  请登录 {info['check_url']} 导出 Cookie 到:")
            cookie_path = os.path.join(COOKIES_DIR, info["cookie_file"])
            print(f"  {cookie_path}")
            all_ok = False

    print()
    if all_ok:
        print("=== 所有平台 Cookie 正常 ===")
    else:
        print("=== 部分平台 Cookie 需要更新 ===")
        sys.exit(1)


if __name__ == "__main__":
    main()