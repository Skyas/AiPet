from pydantic_settings import BaseSettings
from pydantic import BaseModel
from typing import Optional
import json, os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "user_config.json")

DEFAULT_CONFIG = {
    "general": {
        "language": "zh-CN",
        "hotkey": "Ctrl+Shift+A",
        "auto_start": False
    },
    "ai": {
        "text_api_url": "https://api.openai.com/v1",
        "text_api_key": "",
        "text_model": "gpt-4o-mini",
        "max_tokens": 2000,
        "temperature": 0.8,
        "top_p": 1.0
    },
    "vision": {
        # ── 主开关 ────────────────────────────────────────────────────────────
        "enabled": False,

        # ── 视觉模型选择 ──────────────────────────────────────────────────────
        # False = 自动路由（多模态文本模型 → 直接用；否则 → 硅基流动默认）
        # True  = 使用下方用户自定义的 Vision 模型配置
        "custom_vision_enabled": False,

        # 硅基流动 Key（默认路由时使用；不填则视觉功能不可用）
        # 注册免费：siliconflow.cn → 控制台 → API密钥 → 新建密钥
        "siliconflow_key": "",

        # 自定义 Vision 模型配置（custom_vision_enabled=True 时生效）
        "api_url": "https://api.siliconflow.cn/v1",
        "api_key": "",
        "model": "Qwen/Qwen2.5-VL-7B-Instruct",

        # ── 注入行为 ──────────────────────────────────────────────────────────
        "inject_on_chat": True,

        # ── 主动互动引擎 ──────────────────────────────────────────────────────
        "proactive_enabled": False,
        "proactive_check_interval": 45,
        "proactive_user_cooldown": 60,
        "proactive_min_interval": 120,
        "proactive_session_id": "default",

        # ── 屏幕记忆 ─────────────────────────────────────────────────────────
        "memory_size": 5,

        # ── 截图 ─────────────────────────────────────────────────────────────
        "capture_region": "fullscreen",
    },
    "voice": {
        "enabled": False,
        "wake_word_enabled": True,
        "stt_enabled": True,
        "tts_enabled": True,
        "wake_word": "你好小爱",
        "wake_word_sensitivity": 0.5,
        "stt_model": "faster-whisper",
        "tts_voice": "zh-CN-XiaoxiaoNeural"
    },
    "qq": {
        "enabled": False,
        "ws_port": 8765,
        "monitor_groups": [],
        "monitor_privates": [],
        "auto_reply": False,
        "notify_method": "popup"
    },
    "window": {
        "width": 300,
        "height": 400,
        "opacity": 0.95,
        "always_on_top": True,
        "position": {"x": 100, "y": 100}
    }
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    merged = _deep_merge(DEFAULT_CONFIG, data)
    return merged


def save_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result