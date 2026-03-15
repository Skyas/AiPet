"""
对话 API 路由 — Phase 2 升级版
视觉路由统一走 api.screen.get_screen_description()，不在这里重复判断。
"""
import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from modules.core.ai_chat import AIChatModule
from modules.core.history import save_message, get_history, clear_history, get_sessions
from modules.prompt_manager import get_prompt

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_chat_module(request: Request) -> AIChatModule:
    return request.app.state.chat_module


@router.post("/send")
async def send_message(request: Request):
    """流式发送消息，支持 Vision 上下文注入。"""
    body       = await request.json()
    user_msg   = body.get("message", "")
    session_id = body.get("session_id", "default")
    prompt_id  = body.get("prompt_id", "default_assistant")

    if not user_msg.strip():
        return {"error": "消息不能为空"}

    config = request.app.state.config
    vcfg   = config.get("vision", {})

    # 通知主动引擎：用户活跃，重置冷却
    proactive_engine = getattr(request.app.state, "proactive_engine", None)
    if proactive_engine:
        proactive_engine.notify_user_activity()

    # 保存用户消息（纯文本，不含 vision 注入）
    save_message(session_id, "user", user_msg)

    # 并行：获取历史 + 截图
    vision_inject_enabled = vcfg.get("enabled") and vcfg.get("inject_on_chat", True)
    vision_task = None
    if vision_inject_enabled:
        vision_task = asyncio.create_task(_capture_for_chat(request.app, vcfg))

    history     = get_history(session_id, limit=20)
    prompt_card = get_prompt(prompt_id) or get_prompt("default_assistant")
    system_prompt = prompt_card.get("system_prompt", "") if prompt_card else ""

    # 等待视觉结果
    vision_result: Optional[dict] = None
    if vision_task:
        try:
            vision_result = await asyncio.wait_for(vision_task, timeout=12.0)
        except Exception as e:
            print(f"[Chat] Vision 注入失败（不影响对话）: {e}")

    # 将视觉信息注入最后一条 user 消息
    vision_memory = getattr(request.app.state, "vision_memory", None)
    if vision_result and history:
        last_msg = history[-1]
        if last_msg["role"] == "user":
            if "b64" in vision_result:
                from modules.core.ai_vision import build_multimodal_user_message
                history[-1] = build_multimodal_user_message(last_msg["content"], vision_result["b64"])
            elif "desc" in vision_result:
                history[-1] = {
                    **last_msg,
                    "content": f"{last_msg['content']}\n\n[当前屏幕画面：{vision_result['desc']}]",
                }
            if vision_memory and "desc" in vision_result:
                vision_memory.add(vision_result["desc"], triggered_by="user_chat")

    # 将屏幕变化摘要注入 system prompt
    if vision_memory:
        screen_ctx = vision_memory.get_context_for_prompt(n=3)
        if screen_ctx:
            system_prompt += f"\n\n[最近观察到的屏幕变化：\n{screen_ctx}]"

    # 流式生成
    chat = get_chat_module(request)

    async def generate():
        full_reply = []
        async for token in chat.chat_stream(history, system_prompt):
            full_reply.append(token)
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        save_message(session_id, "assistant", "".join(full_reply))
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _capture_for_chat(app, vcfg: dict) -> Optional[dict]:
    """
    截图并根据路由决定返回格式：
      multimodal → {"b64": "..."}   直接嵌图
      其他       → {"desc": "..."}  文字描述
    路由判断委托给 get_screen_description / get_vision_route，不在这里重复。
    """
    from modules.core.screen_capture import capture_screen
    from modules.core.ai_vision import get_vision_route

    config = app.state.config
    region = vcfg.get("capture_region", "fullscreen")
    b64, _, _ = await asyncio.to_thread(capture_screen, region)

    route = get_vision_route(config)
    if route == "multimodal":
        # 返回 b64，由上层直接嵌入 chat 请求
        return {"b64": b64}
    else:
        # 用统一的 get_screen_description 获取文字描述
        from api.screen import get_screen_description
        desc = await get_screen_description(app, b64)
        return {"desc": desc}


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 40):
    return {"messages": get_history(session_id, limit)}


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    clear_history(session_id)
    return {"ok": True}


@router.get("/sessions")
async def list_sessions():
    return {"sessions": get_sessions()}