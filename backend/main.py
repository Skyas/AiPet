import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn

from config.settings import load_config
from modules.core.ai_chat import AIChatModule
from modules.core.history import init_db
from api.chat import router as chat_router
from api.settings_api import router as settings_router
from api.prompts_api import router as prompts_router
from version import __version__, APP_NAME

config = load_config()
init_db()

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI(title=APP_NAME, version=__version__)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(prompts_router)

app.state.config = config
app.state.chat_module = AIChatModule(config)
app.state.sio = sio

@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] connected: {sid}")
    await sio.emit("server_info", {
        "version": __version__,
        "modules": {"voice": False, "qq": False}
    }, to=sid)

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] disconnected: {sid}")

@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}

from socketio import ASGIApp
socket_app = ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    print("[AiPet] Starting on http://localhost:8001")
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8001, reload=False)