# ComfyUI Workflow 配置参考

## API 调用方式

ComfyUI 提供 REST API 用于程序化调用：

```
POST http://127.0.0.1:8188/api/prompt
Content-Type: application/json
```

请求体是一个包含所有节点定义的 JSON workflow。

## 基础 txt2img Workflow 模板

```json
{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "cfg": 7.0,
      "denoise": 1.0,
      "latent_image": ["5", 0],
      "model": ["4", 0],
      "negative": ["7", 0],
      "positive": ["6", 0],
      "sampler_name": "euler_ancestral",
      "scheduler": "normal",
      "seed": 0,
      "steps": 30
    }
  },
  "4": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    }
  },
  "5": {
    "class_type": "EmptyLatentImage",
    "inputs": {
      "batch_size": 1,
      "height": 1024,
      "width": 1024
    }
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "clip": ["4", 1],
      "text": "正向 prompt"
    }
  },
  "7": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "clip": ["4", 1],
      "text": "负向 prompt"
    }
  },
  "8": {
    "class_type": "VAEDecode",
    "inputs": {
      "samples": ["3", 0],
      "vae": ["4", 2]
    }
  },
  "9": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "pipeline_output",
      "images": ["8", 0]
    }
  }
}
```

## 参数说明

| 参数 | 节点 | 默认值 | 说明 |
|------|------|--------|------|
| cfg | KSampler | 7.0 | CFG Scale，越高越贴合 prompt（5-12） |
| steps | KSampler | 30 | 采样步数（20-50） |
| sampler_name | KSampler | euler_ancestral | 采样器 |
| scheduler | KSampler | normal | 调度器 |
| seed | KSampler | 0 | 随机种子（变体通过改 seed 实现） |
| denoise | KSampler | 1.0 | 去噪强度（txt2img 始终为 1.0） |
| width | EmptyLatentImage | 1024 | 图片宽度 |
| height | EmptyLatentImage | 1024 | 图片高度 |
| batch_size | EmptyLatentImage | 1 | 每次生成张数 |

## 多版本生成策略

每个场景生成 N 个变体：

```python
import random

for variant in range(variants):
    workflow["3"]["inputs"]["seed"] = random.randint(0, 2**32)
    workflow["6"]["inputs"]["text"] = f"{base_prompt}, {style_suffix}"
    # POST workflow to ComfyUI API
```

变体差异来源：
1. **不同 seed** — 相同 prompt，不同随机种子
2. **微调 prompt** — 同一场景，略微调整风格关键词
3. **不同模型** — 使用不同 checkpoint（高级用法）

## 推荐 Checkpoint 模型

| 模型 | 风格 | 大小 | 推荐场景 |
|------|------|------|---------|
| SDXL 1.0 | 通用 | 6.9GB | 默认选择 |
| DreamShaper XL | 美术 | 6.5GB | 插画/概念艺术 |
| RealVisXL | 写实 | 6.5GB | 照片级写实 |
| Animagine XL | 动漫 | 6.5GB | 二次元风格 |

模型存放路径：`~/ComfyUI/models/checkpoints/`

## HuggingFace 镜像（国内下载）

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
# 然后用 huggingface-cli 下载
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 --local-dir ~/ComfyUI/models/checkpoints/
```

## 常用采样器对比

| 采样器 | 速度 | 质量 | 推荐度 |
|--------|------|------|--------|
| euler_ancestral | 快 | 好 | 默认推荐 |
| dpmpp_2m | 中 | 很好 | 高质量 |
| dpmpp_sde | 慢 | 最好 | 精细图 |
| euler | 快 | 中 | 快速预览 |

## 图片尺寸建议

| 平台 | 推荐比例 | 推荐尺寸 |
|------|----------|----------|
| 通用 | 1:1 | 1024x1024 |
| 竖版短视频 | 9:16 | 768x1344 |
| 横版封面 | 16:9 | 1344x768 |
| 小红书 | 3:4 | 768x1024 |