from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from modules.core.ai_chat import AIChatModule
from modules.core.history import save_message, get_history, clear_history, get_sessions
from modules.prompt_manager import get_prompt
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_chat_module(request: Request) -> AIChatModule:
    return request.app.state.chat_module


@router.post("/send")
async def send_message(request: Request):
    """流式发送消息"""
    body = await request.json()
    user_msg: str = body.get("message", "")
    session_id: str = body.get("session_id", "default")
    prompt_id: str = body.get("prompt_id", "default_assistant")

    if not user_msg.strip():
        return {"error": "消息不能为空"}

    # 保存用户消息
    save_message(session_id, "user", user_msg)

    # 获取历史
    history = get_history(session_id, limit=20)

    # 获取 system prompt
    prompt_card = get_prompt(prompt_id) or get_prompt("default_assistant")
    system_prompt = prompt_card.get("system_prompt", "") if prompt_card else ""

    chat = get_chat_module(request)

    async def generate():
        full_reply = []
        async for token in chat.chat_stream(history, system_prompt):
            full_reply.append(token)
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        # 保存 AI 回复
        save_message(session_id, "assistant", "".join(full_reply))
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


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
