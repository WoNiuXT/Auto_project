"""TTS 语音合成模块。
使用 edge-tts (Microsoft Edge TTS) 将文案旁白转为语音。
每个场景生成独立的 MP3 文件，同时输出字幕时间轴。
"""
import asyncio
import json
import os
import re
from typing import Dict, List, Optional


# 中文语音推荐列表
CHINESE_VOICES = {
    "female_warm": "zh-CN-XiaoxiaoNeural",      # 女声 温暖亲切
    "female_cheerful": "zh-CN-XiaoyiNeural",     # 女声 活泼
    "male_calm": "zh-CN-YunxiNeural",            # 男声 沉稳
    "male_narration": "zh-CN-YunjianNeural",     # 男声 播音
    "female_news": "zh-CN-XiaochenNeural",       # 女声 新闻
}


class TTSGenerator:
    """edge-tts 语音合成器。"""

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural",
                 rate: str = "+0%", volume: str = "+0%"):
        self.voice = voice
        self.rate = rate
        self.volume = volume

    async def _generate_one(self, text: str, output_path: str) -> Dict:
        """生成单条语音 + 字幕时间轴。"""
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
        )

        subtitles = []
        audio_path = output_path

        # 收集字幕事件
        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    subtitles.append({
                        "text": chunk["text"],
                        "offset": chunk["offset"] / 10_000_000,      # 100ns -> seconds
                        "duration": chunk["duration"] / 10_000_000,
                    })

        # 计算总时长
        total_duration = 0.0
        if subtitles:
            last = subtitles[-1]
            total_duration = last["offset"] + last["duration"]

        return {
            "audio_path": audio_path,
            "duration": total_duration,
            "subtitles": subtitles,
        }

    def generate_one(self, text: str, output_path: str) -> Dict:
        """同步接口：生成单条语音。"""
        return asyncio.run(self._generate_one(text, output_path))

    def generate_scenes(self, scenes: List[Dict], output_dir: str,
                        prefix: str = "scene") -> List[Dict]:
        """为每个分镜场景生成语音。
        
        Args:
            scenes: [{"scene_id": 1, "narration": "...", ...}, ...]
            output_dir: 输出目录
            prefix: 文件名前缀
            
        Returns:
            [{"scene_id": 1, "audio_path": "...", "duration": 3.5, 
              "subtitles": [...]}, ...]
        """
        os.makedirs(output_dir, exist_ok=True)
        results = []

        for scene in scenes:
            sid = scene.get("scene_id", len(results) + 1)
            narration = scene.get("narration", "").strip()
            if not narration:
                print(f"  [SKIP] 场景 {sid} 无旁白文本")
                continue

            audio_file = os.path.join(output_dir, f"{prefix}{sid:02d}_audio.mp3")
            print(f"  [TTS] 场景 {sid}: {narration[:30]}...")

            try:
                result = self.generate_one(narration, audio_file)
                result["scene_id"] = sid
                result["narration"] = narration
                print(f"    -> {audio_file} ({result['duration']:.1f}s)")
                results.append(result)
            except Exception as e:
                print(f"    -> [FAIL] TTS 失败: {e}")

        # 保存字幕时间轴
        srt_path = os.path.join(output_dir, "subtitles.json")
        with open(srt_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  [TTS] 字幕时间轴: {srt_path}")

        return results

    def generate_srt(self, tts_results: List[Dict], output_path: str) -> str:
        """生成 SRT 字幕文件。
        
        将每个场景的 word-level 时间轴聚合为句子级别的 SRT 字幕。
        """
        srt_lines = []
        idx = 1
        cumulative_offset = 0.0

        for result in tts_results:
            narration = result.get("narration", "")
            duration = result.get("duration", 0)

            if not narration:
                cumulative_offset += duration
                continue

            # 将旁白按标点分句
            sentences = re.split(r'([。！？，；、])', narration)
            # 合并标点到前一个句子
            merged = []
            for s in sentences:
                if not s.strip():
                    continue
                if s in '。！？，；、' and merged:
                    merged[-1] += s
                else:
                    merged.append(s)

            # 按句子数量均匀分配时间
            if merged:
                per_sentence = duration / len(merged)
                for i, sent in enumerate(merged):
                    start = cumulative_offset + i * per_sentence
                    end = start + per_sentence
                    srt_lines.append(f"{idx}")
                    srt_lines.append(f"{self._format_time(start)} --> {self._format_time(end)}")
                    srt_lines.append(sent.strip())
                    srt_lines.append("")
                    idx += 1

            cumulative_offset += duration

        srt_content = "\n".join(srt_lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        print(f"  [SRT] 字幕文件: {output_path}")
        return srt_content

    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化为 SRT 时间码 HH:MM:SS,mmm。"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


if __name__ == "__main__":
    # 快速测试
    tts = TTSGenerator(voice="zh-CN-XiaoxiaoNeural")
    result = tts.generate_one("你好，这是一条测试语音。", "test_tts.mp3")
    print(f"Duration: {result['duration']:.1f}s")
    print(f"Subtitles: {len(result['subtitles'])} words")
