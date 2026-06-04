#!/usr/bin/env python3
"""检查 ComfyUI 安装状态和运行状态。"""
import sys
import os
import json
import urllib.request
import urllib.error

# ComfyUI 需要 Python 3.10+，优先使用 C:\Python310
PYTHON310 = r"C:\Python310\python.exe"
COMFYUI_DIR = os.path.expanduser("~/ComfyUI")


def check_comfyui_installed():
    """检查 ComfyUI 是否已安装。"""
    possible_paths = [
        COMFYUI_DIR,
        os.path.expanduser("~\\ComfyUI"),
        "C:\\ComfyUI",
        os.path.join(os.environ.get("COMFYUI_PATH", ""), ""),
    ]
    for path in possible_paths:
        if path and os.path.isdir(os.path.join(path, "comfy")):
            return path
    return None


def check_comfyui_running(host="127.0.0.1", port=8188):
    """检查 ComfyUI 服务是否在运行。"""
    try:
        url = f"http://{host}:{port}/system_stats"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return True, data
    except (urllib.error.URLError, ConnectionRefusedError, OSError):
        return False, None


def main():
    print("=== ComfyUI 状态检查 ===\n")

    # 检查安装
    install_path = check_comfyui_installed()
    if install_path:
        print(f"[OK] ComfyUI 已安装: {install_path}")
    else:
        print("[FAIL] 未找到 ComfyUI 安装目录")
        print(f"  运行 python scripts/install_comfyui.py 进行安装")
        sys.exit(1)

    # 检查运行状态
    running, stats = check_comfyui_running()
    if running:
        print("[OK] ComfyUI 服务运行中 (http://127.0.0.1:8188)")
        if stats:
            devices = stats.get("devices", [])
            for d in devices:
                name = d.get("name", "unknown")
                vram = d.get("vram_total", 0) / (1024**3)
                print(f"  设备: {name}, 显存: {vram:.1f}GB")
    else:
        print("[FAIL] ComfyUI 服务未运行")
        python_cmd = PYTHON310 if os.path.isfile(PYTHON310) else "python"
        print(f"  启动命令: cd {install_path} && {python_cmd} main.py --listen 127.0.0.1 --port 8188 --lowvram")
        sys.exit(1)

    # 检查模型
    models_dir = os.path.join(install_path, "models", "checkpoints")
    if os.path.isdir(models_dir):
        models = [f for f in os.listdir(models_dir) if f.endswith((".safetensors", ".ckpt", ".pt"))]
        if models:
            print(f"\n[OK] 找到 {len(models)} 个模型:")
            for m in models:
                size = os.path.getsize(os.path.join(models_dir, m)) / (1024**3)
                print(f"  - {m} ({size:.1f}GB)")
        else:
            print("\n[WARN] 未找到 checkpoint 模型，请下载后放到:")
            print(f"  {models_dir}")
    else:
        print(f"\n[WARN] 模型目录不存在: {models_dir}")

    print("\n=== 检查完成 ===")


if __name__ == "__main__":
    main()