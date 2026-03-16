"""
屏幕交互 API 路由

端点列表：
  POST /api/screen/analyze         — 手动触发截图 + 视觉分析 + AI 点评（SSE 流式）
  POST /api/screen/proactive/start — 启动主动互动引擎
  POST /api/screen/proactive/stop  — 停止主动互动引擎
  GET  /api/screen/status          — 查询引擎状态与最近一次分析结果
  GET  /api/screen/monitors        — 枚举系统显示器
"""
import asyncio
import json
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/screen", tags=["screen"])

# chat.py 也会 import 这个函数，集中路由逻辑，避免重复


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── 核心：获取画面文字描述（路由已内聚在这里） ─────────────────────────────────

async def get_screen_description(app, b64: str, prompt: Optional[str] = None) -> str:
    """
    根据五级路由规则，获取当前截图的文字描述。

    - multimodal 路由：用文本模型客户端直接看图（不走 vision_module）
    - custom / default 路由：走 vision_module.analyze_image()

    这个函数是 screen.py 唯一需要关心"用哪个模型"的地方，
    其他地方直接调用它，不用再做路由判断。
    """
    from modules.core.ai_vision import get_vision_route, build_multimodal_user_message

    config = app.state.config
    route  = get_vision_route(config)

    if route == "multimodal":
        # 用文本模型客户端直接看图，避免用错 key/url
        ai_cfg     = config.get("ai", {})
        chat_module = app.state.chat_module

        describe_prompt = prompt or (
            "请用中文简洁描述这张屏幕截图中用户正在做什么。"
            "重点关注：运行的游戏或应用、当前操作、关键 UI 元素（如地图、血量、计分板等）。"
            "保持客观，100 字以内。"
        )
        user_msg = build_multimodal_user_message(describe_prompt, b64)
        desc = await chat_module.chat_once([user_msg], system_prompt="")
        return desc.strip()
    else:
        # custom 或 default：走 vision_module（已内置正确的 client 选择）
        vision_mod = app.state.vision_module
        return await vision_mod.analyze_image(b64, vision_prompt=prompt, detail="low")


# ── 手动分析流水线 ────────────────────────────────────────────────────────────

async def _manual_pipeline(app) -> AsyncGenerator[str, None]:
    from modules.core.screen_capture import capture_screen
    from modules.core.ai_vision import get_vision_route, build_multimodal_user_message
    from modules.prompt_manager import get_prompt

    config = app.state.config
    vcfg   = config.get("vision", {})
    vision_memory = app.state.vision_memory
    route  = get_vision_route(config)

    # 1. 截图
    yield sse({"status": "capturing"})
    try:
        region = vcfg.get("capture_region", "fullscreen")
        b64, w, h = await asyncio.to_thread(capture_screen, region)
    except Exception as e:
        yield sse({"error": f"截图失败: {e}"}); return

    # 2. 视觉分析（获取文字描述，供"画面识别"展示和记忆存储）
    yield sse({"status": "analyzing_vision"})
    try:
        vision_desc = await get_screen_description(app, b64)
    except Exception as e:
        yield sse({"error": f"视觉分析失败: {e}"}); return

    yield sse({"vision_desc": vision_desc})
    vision_memory.add(vision_desc, triggered_by="manual")

    # 3. AI 点评（流式）
    yield sse({"status": "generating"})

    prompt_card      = _get_active_prompt(app)
    commentary_tmpl  = prompt_card.get("game_commentary_prompt", "")
    base_system      = prompt_card.get("system_prompt", "")

    if commentary_tmpl:
        user_content = f"{commentary_tmpl}\n\n【当前画面】{vision_desc}"
    else:
        user_content = (
            "你是用户的 AI 桌宠，正在陪他玩游戏或使用电脑。"
            "请根据以下屏幕描述，用你的人设风格发表简短评论或给出一条小建议（50~80字）。"
            f"\n\n【当前画面】{vision_desc}"
        )

    # multimodal 路由：把截图直接嵌入点评请求，让 AI 亲眼看（更准确）
    if route == "multimodal":
        user_msg = build_multimodal_user_message(user_content, b64)
        messages = [user_msg]
    else:
        messages = [{"role": "user", "content": user_content}]

    # 注入屏幕变化摘要
    screen_ctx = vision_memory.get_context_for_prompt(n=3)
    if screen_ctx:
        base_system += f"\n\n[最近观察到的屏幕变化：\n{screen_ctx}]"

    chat_module = app.state.chat_module
    full_text   = []
    try:
        async for token in chat_module.chat_stream(messages, system_prompt=base_system):
            full_text.append(token)
            yield sse({"token": token})
    except Exception as e:
        yield sse({"error": f"AI 点评生成失败: {e}"}); return

    yield sse({"done": True, "full_text": "".join(full_text)})


def _get_active_prompt(app) -> dict:
    try:
        from modules.prompt_manager import get_prompt
        active_id = getattr(app.state, "active_prompt_id", "default_assistant")
        return get_prompt(active_id) or {}
    except Exception:
        return {}


# ── REST 端点 ─────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def manual_analyze(request: Request):
    async def stream():
        async for chunk in _manual_pipeline(request.app):
            yield chunk

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/proactive/start")
async def start_proactive(request: Request):
    engine = request.app.state.proactive_engine
    if engine.is_running:
        return {"ok": False, "msg": "主动引擎已在运行"}
    engine.start()
    request.app.state.config.setdefault("vision", {})["proactive_enabled"] = True
    return {"ok": True, "msg": "主动引擎已启动"}


@router.post("/proactive/stop")
async def stop_proactive(request: Request):
    engine = request.app.state.proactive_engine
    engine.stop()
    request.app.state.config.setdefault("vision", {})["proactive_enabled"] = False
    return {"ok": True, "msg": "主动引擎已停止"}


@router.get("/status")
async def get_status(request: Request):
    engine       = request.app.state.proactive_engine
    vision_memory = request.app.state.vision_memory
    latest       = vision_memory.get_latest()
    return {
        "proactive_running": engine.is_running,
        "last_timestamp":    latest.timestamp       if latest else None,
        "last_vision_desc":  latest.vision_desc     if latest else "",
        "last_reply":        latest.associated_reply if latest else "",
        "observation_count": len(vision_memory),
    }


@router.get("/monitors")
async def get_monitors():
    try:
        from modules.core.screen_capture import list_monitors
        monitors = await asyncio.to_thread(list_monitors)
        return {"monitors": monitors}
    except Exception as e:
        return {"monitors": [], "error": str(e)}