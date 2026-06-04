#!/usr/bin/env python3
"""检查 DailyHotApi Docker 容器状态。"""
import sys
import json
import urllib.request
import urllib.error
import subprocess


def check_docker_running():
    """检查 Docker 是否运行。"""
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_container_running(container_name="dailyhot-api"):
    """检查容器是否在运行。"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        return container_name in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_api_responsive(host="127.0.0.1", port=6688):
    """检查 API 是否可访问。"""
    try:
        url = f"http://{host}:{port}/"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, ConnectionRefusedError, OSError):
        return False


def main():
    print("=== DailyHotApi 状态检查 ===\n")

    # 检查 Docker
    print("[1/3] 检查 Docker...")
    if not check_docker_running():
        print("[FAIL] Docker 未运行，请启动 Docker Desktop")
        sys.exit(1)
    print("[OK] Docker 运行中")

    # 检查容器
    print("\n[2/3] 检查 dailyhot-api 容器...")
    if not check_container_running():
        print("[FAIL] dailyhot-api 容器未运行")
        print("  运行: docker compose up -d dailyhot-api")
        sys.exit(1)
    print("[OK] dailyhot-api 容器运行中")

    # 检查 API
    print("\n[3/3] 检查 API 响应...")
    if not check_api_responsive():
        print("[FAIL] DailyHotApi API 无响应 (http://localhost:6688)")
        print("  运行: docker compose restart dailyhot-api")
        print("  查看日志: docker logs dailyhot-api")
        sys.exit(1)
    print("[OK] API 响应正常")

    # 测试实际数据
    print("\n测试数据获取...")
    try:
        url = "http://localhost:6688/"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            if isinstance(data, list):
                print(f"[OK] 返回 {len(data)} 条热搜数据")
            elif isinstance(data, dict):
                routes = [k for k in data.keys()]
                print(f"[OK] 支持平台: {', '.join(routes[:8])}...")
    except Exception as e:
        print(f"[WARN] 数据获取异常: {e}")

    print("\n=== 检查完成 ===")


if __name__ == "__main__":
    main()