"""配置加载模块。读取 pipeline_config.toml + .env。"""
import os
import toml
from pathlib import Path


def load_dotenv(env_path: str = ".env") -> dict:
    """简易 .env 加载（不依赖 python-dotenv）。"""
    env = {}
    if not os.path.isfile(env_path):
        return env
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


class Config:
    """流水线配置管理器。"""

    def __init__(self, config_path: str = "pipeline_config.toml", env_path: str = ".env"):
        self._config_path = config_path
        self._data = {}
        self._env = load_dotenv(env_path)
        self._load()

    def _load(self):
        """加载 TOML 配置文件。"""
        if os.path.isfile(self._config_path):
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._data = toml.load(f)
        else:
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")

    def get(self, section: str, key: str, default=None):
        """获取配置值，优先从 .env 读取密钥类字段。"""
        # 密钥类字段从 .env 读取
        if key in ("api_key", "password", "secret", "token"):
            env_key = f"{section.upper()}_{key.upper()}"
            if env_key in self._env:
                return self._env[env_key]
            # 特殊处理 MIMO
            if section == "mimo" and "MIMO_API_KEY" in self._env:
                return self._env["MIMO_API_KEY"]
        return self._data.get(section, {}).get(key, default)

    def section(self, name: str) -> dict:
        """获取整个配置段。"""
        return self._data.get(name, {})

    @property
    def proxy(self) -> dict:
        """获取代理配置。"""
        p = self.section("proxy")
        return {"http": p.get("http"), "https": p.get("https")} if p else {}

    @property
    def output_dir(self) -> str:
        return "pipeline_output"

    @property
    def review_dir(self) -> str:
        return "photo_review"

    @property
    def cookies_dir(self) -> str:
        return "cookies"