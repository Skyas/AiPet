"""
Prompt 卡片管理（类 TavernAI 风格）
"""
import json, os, glob
from datetime import datetime

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

DEFAULT_PROMPT = {
    "id": "default_assistant",
    "name": "默认助手",
    "version": "1.0.0",
    "description": "通用 AI 助手人格",
    "author": "User",
    "system_prompt": "你是一个聪明、友善的 AI 桌宠，名叫小爱。你运行在用户的桌面上，随时待命。回答简洁有趣，偶尔用颜文字，不要过于正式。",
    "greeting": "你好！有什么可以帮你的吗？(ﾟ▽ﾟ)/",
    "persona": {
        "name": "小爱",
        "personality": "活泼、聪明、有点傲娇",
        "speaking_style": "口语化，偶尔用颜文字"
    },
    "context_template": "{{system_prompt}}",
    "tags": ["通用"],
    "created_at": datetime.now().strftime("%Y-%m-%d"),
    "updated_at": datetime.now().strftime("%Y-%m-%d")
}


def _ensure_dir():
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    default_path = os.path.join(PROMPTS_DIR, "default_assistant.json")
    if not os.path.exists(default_path):
        with open(default_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PROMPT, f, ensure_ascii=False, indent=2)


def list_prompts() -> list[dict]:
    _ensure_dir()
    result = []
    for path in glob.glob(os.path.join(PROMPTS_DIR, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                result.append(data)
        except Exception:
            pass
    return sorted(result, key=lambda x: x.get("name", ""))


def get_prompt(prompt_id: str) -> dict | None:
    _ensure_dir()
    path = os.path.join(PROMPTS_DIR, f"{prompt_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_prompt(data: dict) -> dict:
    _ensure_dir()
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    if "id" not in data or not data["id"]:
        import uuid
        data["id"] = f"prompt_{uuid.uuid4().hex[:8]}"
    if "created_at" not in data:
        data["created_at"] = data["updated_at"]
    path = os.path.join(PROMPTS_DIR, f"{data['id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def delete_prompt(prompt_id: str) -> bool:
    if prompt_id == "default_assistant":
        return False  # 保护默认 prompt
    path = os.path.join(PROMPTS_DIR, f"{prompt_id}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
