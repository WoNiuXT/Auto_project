"""MiMo API 文案生成器。

职责：
- 管理 prompt 模板（按 persona 分类）
- 调用 MiMo Chat Completions API
- 解析返回的结构化分镜脚本 JSON
- 重试 + 错误处理（tenacity）
"""
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Optional


# prompt 模板（内联精简版，完整版见 references/prompt-templates.md）
PERSONA_TEMPLATES = {
    "知识科普博主": {
        "system": (
            "你是一个知识科普博主，擅长用通俗易懂的语言解释复杂概念。\n"
            "受众：18-35岁对知识感兴趣的用户\n"
            "语气：轻松有趣，偶尔用比喻，避免学术腔\n"
            "结构：开头抛出疑问 -> 中间解释原理 -> 结尾总结启发"
        ),
        "style_keywords": ["digital art", "futuristic", "clean", "infographic"],
    },
    "生活技巧博主": {
        "system": (
            "你是一个生活技巧博主，专注于实用、可操作的生活窍门。\n"
            "受众：25-40岁注重生活品质的用户\n"
            "语气：亲切温暖，像朋友分享经验"
        ),
        "style_keywords": ["photorealistic", "natural light", "warm tones", "lifestyle"],
    },
    "科技资讯博主": {
        "system": (
            "你是一个科技资讯博主，第一时间解读最新科技动态。\n"
            "受众：20-35岁科技爱好者\n"
            "语气：专业但不枯燥，有观点有态度"
        ),
        "style_keywords": ["3d render", "digital art", "cyberpunk", "blue and purple"],
    },
    "情感故事博主": {
        "system": (
            "你是一个情感故事博主，用故事打动人心。\n"
            "受众：20-40岁有情感共鸣需求的用户\n"
            "语气：温柔细腻，有画面感"
        ),
        "style_keywords": ["cinematic", "warm tones", "soft light", "illustration"],
    },
}


class ScriptGenerator:
    """MiMo API 文案生成器。"""

    def __init__(self, api_key: str, base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
                 model: str = "mimo-v2.5-pro", temperature: float = 0.8,
                 max_tokens: int = 2000, proxy: dict = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.proxy = proxy or {}

    def _build_prompt(self, topic: str, persona: str, scene_count: int,
                      audience: str = "", tone: str = "") -> str:
        """构建发送给 LLM 的 user prompt。"""
        template = PERSONA_TEMPLATES.get(persona, PERSONA_TEMPLATES["知识科普博主"])
        system_prompt = template["system"]
        if audience:
            system_prompt += f"\n受众：{audience}"
        if tone:
            system_prompt += f"\n语气：{tone}"

        user_prompt = (
            f"请为以下话题生成 {scene_count} 个分镜脚本。\n\n"
            f"话题：{topic}\n\n"
            f"要求：\n"
            f"1. 每个分镜包含 scene_id, narration（中文配文）, "
            f"image_prompt（英文生图描述，详细具体）, style_keywords（风格标签列表）\n"
            f"2. narration 口语化，适合短视频\n"
            f"3. image_prompt 用英文，包含画面主体、构图、色调、风格\n"
            f"4. image_prompt 避免文字/字母/数字\n\n"
            f"请严格按以下 JSON 格式返回：\n"
            f'{{"topic": "{topic}", "persona": "{persona}", "scenes": ['
            f'{{"scene_id": 1, "narration": "...", "image_prompt": "...", "style_keywords": ["...", "..."]}}, ...'
            f"]}}"
        )
        return system_prompt, user_prompt

    def generate(self, topic: str, persona: str = "知识科普博主",
                 scene_count: int = 5, audience: str = "",
                 tone: str = "") -> Optional[Dict]:
        """调用 MiMo API 生成分镜脚本。

        Returns:
            解析后的分镜脚本 dict，或 None（失败时）
        """
        system_prompt, user_prompt = self._build_prompt(
            topic, persona, scene_count, audience, tone
        )

        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }).encode("utf-8")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        # 重试逻辑（最多 3 次）
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"]
                    # 提取 JSON（可能被 markdown 包裹）
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    return json.loads(content.strip())
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"  [WARN] 解析失败 (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    # 最后一次尝试降低 temperature
                    self.temperature = max(0.3, self.temperature - 0.3)
            except urllib.error.URLError as e:
                print(f"  [WARN] API 请求失败 (attempt {attempt+1}/3): {e}")
                import time
                time.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s

        return None