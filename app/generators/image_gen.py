"""ComfyUI 本地生图引擎。
职责:
- 构建 ComfyUI txt2img workflow JSON
- 管理 prompt 变体（不同 seed）
- 调用 ComfyUI API 生成图片
- 下载图片到 pipeline_output + 生成 manifest
"""
import json
import os
import random
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, List, Optional


# 通用负面 prompt
NEGATIVE_PROMPT = (
    "text, watermark, logo, signature, blurry, low quality, distorted, "
    "deformed, ugly, bad anatomy, extra limbs, missing fingers, "
    "jpeg artifacts, cropped, out of frame"
)


class ImageGenerator:
    """ComfyUI 本地生图引擎。"""

    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188",
                 width: int = 1024, height: int = 1024,
                 cfg: float = 7.0, steps: int = 30,
                 sampler: str = "euler_ancestral",
                 scheduler: str = "normal",
                 variants: int = 3,
                 checkpoint: str = "sd_xl_base_1.0.safetensors"):
        self.comfyui_url = comfyui_url.rstrip("/")
        self.width = width
        self.height = height
        self.cfg = cfg
        self.steps = steps
        self.sampler = sampler
        self.scheduler = scheduler
        self.variants = variants
        self.checkpoint = checkpoint

    def _build_workflow(self, positive_prompt: str, seed: int,
                        filename_prefix: str = "pipeline") -> Dict:
        """构建 ComfyUI txt2img workflow JSON。"""
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": self.cfg,
                    "denoise": 1.0,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": self.sampler,
                    "scheduler": self.scheduler,
                    "seed": seed,
                    "steps": self.steps,
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": self.checkpoint},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": self.height,
                    "width": self.width,
                },
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["4", 1], "text": positive_prompt},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["4", 1], "text": NEGATIVE_PROMPT},
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": filename_prefix,
                    "images": ["8", 0],
                },
            },
        }

    def _submit_prompt(self, workflow: Dict) -> Optional[str]:
        """提交 workflow 到 ComfyUI，返回 prompt_id。"""
        url = f"{self.comfyui_url}/api/prompt"
        payload = json.dumps({"prompt": workflow}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("prompt_id")
        except Exception as e:
            print(f"  [ERROR] ComfyUI 提交失败: {e}")
            return None

    def _wait_result(self, prompt_id: str, timeout: int = 600) -> Optional[Dict]:
        """等待生图完成，返回结果信息。"""
        url = f"{self.comfyui_url}/history/{prompt_id}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if prompt_id in data:
                        return data[prompt_id]
            except Exception:
                pass
            time.sleep(2)
        print(f"  [ERROR] ComfyUI 超时 ({timeout}s)")
        return None

    def _download_image(self, filename: str, subfolder: str = "",
                        file_type: str = "output") -> Optional[bytes]:
        """从 ComfyUI 下载生成的图片。"""
        params = urllib.parse.urlencode({
            "filename": filename,
            "subfolder": subfolder,
            "type": file_type,
        })
        url = f"{self.comfyui_url}/view?{params}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as e:
            print(f"  [ERROR] 图片下载失败 ({filename}): {e}")
            return None

    def _extract_images_from_history(self, history: Dict) -> List[Dict]:
        """从 ComfyUI history 结果中提取图片信息。"""
        images = []
        outputs = history.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    images.append(img_info)
        return images

    def generate_scene(self, scene: Dict, output_dir: str,
                       scene_index: int) -> List[Dict]:
        """为单个场景生成多版本图片。
        Args:
            scene: 分镜数据 {scene_id, image_prompt, style_keywords, ...}
            output_dir: 输出目录
            scene_index: 场景序号（用于文件命名）

        Returns:
            [{path, seed, variant}, ...]
        """
        base_prompt = scene.get("image_prompt", "")
        style_kw = scene.get("style_keywords", [])
        style_suffix = ", ".join(style_kw) if style_kw else "digital art"
        full_prompt = f"{base_prompt}, {style_suffix}"

        results = []
        for v in range(1, self.variants + 1):
            seed = random.randint(0, 2**32 - 1)
            prefix = f"scene{scene_index:02d}_v{v}"
            workflow = self._build_workflow(full_prompt, seed, filename_prefix=prefix)

            print(f"    scene{scene_index}_v{v} (seed={seed})...")
            prompt_id = self._submit_prompt(workflow)
            if not prompt_id:
                continue

            history = self._wait_result(prompt_id)
            if not history:
                continue

            # 从 history 中提取生成的图片并下载保存
            gen_images = self._extract_images_from_history(history)
            if not gen_images:
                print(f"    [WARN] scene{scene_index}_v{v} 无输出图片")
                continue

            # 通常取第一张图
            img_info = gen_images[0]
            img_filename = img_info.get("filename", "")
            img_subfolder = img_info.get("subfolder", "")

            # 下载图片
            img_data = self._download_image(img_filename, img_subfolder)
            if not img_data:
                continue

            # 保存到 output_dir
            local_filename = f"{scene_index:02d}_v{v}.png"
            local_path = os.path.join(output_dir, local_filename)
            with open(local_path, "wb") as f:
                f.write(img_data)

            print(f"    [OK] 已保存: {local_path} ({len(img_data) / 1024:.0f} KB)")

            results.append({
                "path": local_path,
                "seed": seed,
                "variant": v,
                "prompt_id": prompt_id,
                "prompt": full_prompt,
                "comfyui_filename": img_filename,
                "size_bytes": len(img_data),
            })

        return results

    def generate_all(self, scenes: List[Dict], output_dir: str) -> List[Dict]:
        """为所有场景生成多版本图片。
        Args:
            scenes: 分镜脚本中的 scenes 列表
            output_dir: 输出目录

        Returns:
            [{scene_id, variant, path, seed, prompt}, ...]
        """
        os.makedirs(output_dir, exist_ok=True)
        all_results = []

        for i, scene in enumerate(scenes, 1):
            scene_id = scene.get("scene_id", i)
            print(f"  生成场景 {scene_id}...")
            results = self.generate_scene(scene, output_dir, scene_id)
            for r in results:
                r["scene_id"] = scene_id
            all_results.extend(results)

        # 生成 manifest
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"  [OK] manifest 已保存: {manifest_path}")

        return all_results