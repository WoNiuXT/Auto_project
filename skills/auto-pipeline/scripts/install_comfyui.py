#!/usr/bin/env python3
"""ComfyUI 安装脚本（Windows）。"""
import subprocess
import sys
import os


def run(cmd, cwd=None):
    """运行命令并打印输出。"""
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=False)
    if result.returncode != 0:
        print(f"  [ERROR] 命令失败，返回码: {result.returncode}")
        return False
    return True


def main():
    print("=== ComfyUI 安装脚本 ===\n")

    install_dir = os.path.expanduser("~/ComfyUI")

    # 检查是否已安装
    if os.path.isdir(os.path.join(install_dir, "comfy")):
        print(f"[OK] ComfyUI 已安装在: {install_dir}")
        print("如需重新安装，请先删除该目录。")
        return

    # 检查 Git
    print("[1/4] 检查 Git...")
    if not run("git --version"):
        print("请先安装 Git: https://git-scm.com/download/win")
        sys.exit(1)

    # 克隆 ComfyUI
    print(f"\n[2/4] 克隆 ComfyUI 到 {install_dir}...")
    parent = os.path.dirname(install_dir)
    if not run(f'git clone https://github.com/comfyanonymous/ComfyUI.git "{install_dir}"', cwd=parent):
        print("克隆失败，检查网络连接或代理设置。")
        sys.exit(1)

    # 安装依赖
    print("\n[3/4] 安装 Python 依赖...")
    if not run(f'{sys.executable} -m pip install -r requirements.txt', cwd=install_dir):
        print("依赖安装失败。")
        sys.exit(1)

    # 提示下载模型
    print("\n[4/4] 模型下载提示...")
    models_dir = os.path.join(install_dir, "models", "checkpoints")
    os.makedirs(models_dir, exist_ok=True)
    print(f"请下载 checkpoint 模型放到: {models_dir}")
    print()
    print("推荐模型：")
    print("  - SDXL 1.0: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0")
    print("  - DreamShaper XL: https://huggingface.co/Lykon/dreamshaper-xl-v2-turbo")
    print()
    print("国内下载（设置 HF 镜像）：")
    print('  $env:HF_ENDPOINT = "https://hf-mirror.com"')
    print()

    # 启动说明
    print("安装完成！启动命令：")
    print(f'  cd "{install_dir}"')
    print("  python main.py --listen 127.0.0.1 --port 8188")
    print()
    print("验证：浏览器打开 http://127.0.0.1:8188")


if __name__ == "__main__":
    main()