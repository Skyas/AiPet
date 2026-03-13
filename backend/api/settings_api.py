from fastapi import APIRouter, Request
from config.settings import load_config, save_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(request: Request):
    return request.app.state.config


@router.put("")
async def update_settings(request: Request):
    body = await request.json()
    config = request.app.state.config
    # 深合并
    from config.settings import _deep_merge
    new_config = _deep_merge(config, body)
    save_config(new_config)
    request.app.state.config = new_config
    # 更新 chat module 配置
    request.app.state.chat_module.update_config(new_config)
    return {"ok": True, "config": new_config}


@router.post("/modules/voice")
async def toggle_voice(request: Request):
    body = await request.json()
    enabled = body.get("enabled", False)
    config = request.app.state.config
    config["voice"]["enabled"] = enabled
    save_config(config)
    return {"ok": True, "enabled": enabled, "message": "语音模块需重启后端生效" if enabled else "已关闭语音模块"}


@router.post("/modules/qq")
async def toggle_qq(request: Request):
    body = await request.json()
    enabled = body.get("enabled", False)
    config = request.app.state.config
    config["qq"]["enabled"] = enabled
    save_config(config)
    return {"ok": True, "enabled": enabled, "message": "QQ模块需重启后端生效" if enabled else "已关闭QQ模块"}
