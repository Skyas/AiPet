"""
视觉分析模块 — 五级优先级路由（修正版）

路由规则（严格按此顺序判断）：
  1. 文本模型是多模态（gpt-4o / gemini / claude-3 / qwen-vl 等）
     → multimodal：图片直接嵌入文本模型请求，无需额外 Vision API
  2. 文本模型不是多模态 + custom_vision_enabled=True
     → custom：使用用户配置的独立 Vision 端点
  3. 文本模型不是多模态 + custom_vision_enabled=False
     → default：硅基流动 Qwen2-VL-7B-Instruct（免费）

"是否自定义"由显式的 custom_vision_enabled 布尔值控制，
不再靠字段值与默认值是否不同来推断，彻底修复"改过再改回"的路由混乱。

Key 分离：
  - default 路由使用 vision.siliconflow_key（专用，不与文本模型 key 混用）
  - custom  路由使用 vision.api_key；为空时降级复用文本模型 key
  - multimodal 路由复用文本模型 client，本模块不介入
"""

from openai import AsyncOpenAI
from typing import Optional

_MULTIMODAL_PATTERNS = [
    "gpt-4o", "gpt-4-turbo", "gpt-4-vision",
    "claude-3", "claude-sonnet", "claude-opus", "claude-haiku",
    "gemini",
    "qwen-vl", "qwen2-vl", "qwenvl",
    "glm-4v", "llava", "internvl", "deepseek-vl", "minicpm-v",
    "vision", "multimodal",
]

_DEFAULT_VISION_URL   = "https://api.siliconflow.cn/v1"
_DEFAULT_VISION_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"


def is_text_model_multimodal(config: dict) -> bool:
    model = config.get("ai", {}).get("text_model", "").lower()
    return any(p in model for p in _MULTIMODAL_PATTERNS)


def get_vision_route(config: dict) -> str:
    """返回 'multimodal' / 'custom' / 'default'。"""
    if is_text_model_multimodal(config):
        return "multimodal"
    if config.get("vision", {}).get("custom_vision_enabled", False):
        return "custom"
    return "default"


def build_multimodal_user_message(text: str, image_b64: str) -> dict:
    """构造 OpenAI 多模态 user 消息，供 multimodal 路由直接嵌入 chat 请求。"""
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": text},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}",
                    "detail": "low",
                },
            },
        ],
    }


def get_vision_status(config: dict) -> dict:
    """返回当前视觉路由状态，供前端状态指示器使用。"""
    route = get_vision_route(config)
    vcfg  = config.get("vision", {})

    if route == "multimodal":
        model = config.get("ai", {}).get("text_model", "")
        return {"route": "multimodal", "label": f"直接使用 {model}", "ready": True, "warning": None}

    elif route == "custom":
        has_key = bool(vcfg.get("api_key") or config.get("ai", {}).get("text_api_key"))
        return {
            "route": "custom",
            "label": f"自定义：{vcfg.get('model', '未指定')}",
            "ready": has_key,
            "warning": None if has_key else "自定义 Vision 模型 API Key 未填写",
        }

    else:  # default
        has_key = bool(vcfg.get("siliconflow_key", "").strip())
        return {
            "route": "default",
            "label": "硅基流动 GLM-4.1V-9B-Thinking（免费）",
            "ready": has_key,
            "warning": None if has_key else "需要填写硅基流动 API Key 才能使用视觉功能",
        }


class AIVisionModule:
    def __init__(self, config: dict):
        self.config = config
        self._clients: dict[str, AsyncOpenAI] = {}
        self._rebuild_clients()

    def _rebuild_clients(self):
        vcfg   = self.config.get("vision", {})
        ai_cfg = self.config.get("ai", {})

        # default：硅基流动，使用专用 siliconflow_key，不与文本模型 key 混用
        sf_key = vcfg.get("siliconflow_key", "").strip() or "sk-placeholder-需填写硅基流动key"
        self._clients["default"] = AsyncOpenAI(api_key=sf_key, base_url=_DEFAULT_VISION_URL)

        # custom：用户自定义；key 为空时降级复用文本模型 key（同一服务商时有用）
        custom_url = vcfg.get("api_url") or _DEFAULT_VISION_URL
        custom_key = vcfg.get("api_key") or ai_cfg.get("text_api_key", "") or "sk-placeholder"
        self._clients["custom"] = AsyncOpenAI(api_key=custom_key, base_url=custom_url)

    def update_config(self, config: dict):
        self.config = config
        self._rebuild_clients()

    def _get_client_and_model(self) -> tuple[AsyncOpenAI, str]:
        vcfg  = self.config.get("vision", {})
        route = get_vision_route(self.config)
        if route == "custom":
            return self._clients["custom"], vcfg.get("model") or _DEFAULT_VISION_MODEL
        return self._clients["default"], _DEFAULT_VISION_MODEL

    async def analyze_image(self, image_b64: str, vision_prompt: Optional[str] = None, detail: str = "low") -> str:
        route = get_vision_route(self.config)

        # default 路由但没填 key → 给出有意义的提示，而不是抛出 401
        if route == "default":
            sf_key = self.config.get("vision", {}).get("siliconflow_key", "").strip()
            if not sf_key:
                raise RuntimeError(
                    "视觉功能需要硅基流动 API Key。\n"
                    "请前往「设置 → 视觉陪玩」填写硅基流动 API Key。\n"
                    "免费注册地址：https://siliconflow.cn"
                )

        if not vision_prompt:
            vision_prompt = (
                "请用中文简洁描述这张屏幕截图中用户正在做什么。"
                "重点关注：运行的游戏或应用、当前操作、关键 UI 元素（如地图、血量等）。"
                "保持客观，100 字以内。"
            )

        client, model = self._get_client_and_model()
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": detail}},
                        {"type": "text", "text": vision_prompt},
                    ],
                }],
                max_tokens=300,
            )
            return resp.choices[0].message.content or ""
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Vision API 调用失败（路由: {route}, 模型: {model}）: {e}") from e