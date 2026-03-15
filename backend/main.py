import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn

from config.settings import load_config
from modules.core.ai_chat import AIChatModule
from modules.core.ai_vision import AIVisionModule
from modules.core.vision_memory import VisionMemory
from modules.core.proactive_engine import ProactiveEngine
from modules.core.history import init_db
from api.chat import router as chat_router
from api.settings_api import router as settings_router
from api.prompts_api import router as prompts_router
from api.screen import router as screen_router
from version import __version__, APP_NAME

# ── 初始化（在 lifespan 外执行，模块级别） ─────────────────────────────────────
config = load_config()
init_db()

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# 先创建 proactive 实例，lifespan 里会用到
proactive = ProactiveEngine()


# ── lifespan：替代废弃的 @app.on_event ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──
    proactive.set_app(app)
    if config.get("vision", {}).get("proactive_enabled", False):
        proactive.start()
        print("[AiPet] 主动互动引擎已随服务启动")

    yield  # ← 服务正常运行期间在这里

    # ── shutdown ──
    proactive.stop()


# ── FastAPI 实例 ───────────────────────────────────────────────────────────────
app = FastAPI(title=APP_NAME, version=__version__, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(prompts_router)
app.include_router(screen_router)

# ── app.state 初始化 ───────────────────────────────────────────────────────────
app.state.config = config
app.state.sio = sio
app.state.chat_module = AIChatModule(config)
app.state.vision_module = AIVisionModule(config)
app.state.vision_memory = VisionMemory(
    max_size=config.get("vision", {}).get("memory_size", 5)
)
app.state.proactive_engine = proactive


# ── Socket.IO 事件 ─────────────────────────────────────────────────────────────
@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] connected: {sid}")
    await sio.emit("server_info", {
        "version": __version__,
        "modules": {
            "voice": False,
            "qq": False,
            "vision": config.get("vision", {}).get("enabled", False),
            "proactive": proactive.is_running,
        },
    }, to=sid)


@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] disconnected: {sid}")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": __version__,
        "proactive_running": proactive.is_running,
    }


from socketio import ASGIApp
socket_app = ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    print(f"[AiPet] Starting {APP_NAME} v{__version__} on http://localhost:8001")
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8001, reload=False)