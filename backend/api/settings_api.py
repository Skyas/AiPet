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
    from config.settings import _deep_merge
    new_config = _deep_merge(config, body)
    save_config(new_config)
    request.app.state.config = new_config

    # 同步更新所有模块的配置（修复：之前漏掉了 vision_module）
    request.app.state.chat_module.update_config(new_config)
    if hasattr(request.app.state, "vision_module"):
        request.app.state.vision_module.update_config(new_config)

    return {"ok": True, "config": new_config}


@router.post("/reload")
async def reload_settings(request: Request):
    """
    从文件重新加载配置并更新所有模块，无需重启后端。
    用于：
      1. 用户直接编辑了 user_config.json 后想让后端生效
      2. 配置页面的「重载配置」按钮
    """
    new_config = load_config()
    request.app.state.config = new_config

    request.app.state.chat_module.update_config(new_config)
    if hasattr(request.app.state, "vision_module"):
        request.app.state.vision_module.update_config(new_config)

    # 同步主动引擎的运行状态
    if hasattr(request.app.state, "proactive_engine"):
        engine = request.app.state.proactive_engine
        should_run = new_config.get("vision", {}).get("proactive_enabled", False)
        if should_run and not engine.is_running:
            engine.start()
        elif not should_run and engine.is_running:
            engine.stop()

    return {"ok": True, "config": new_config, "message": "配置已重载"}


@router.get("/vision-status")
async def get_vision_status(request: Request):
    """
    返回当前视觉路由状态，供设置界面的状态指示器使用。
    前端可在 Vision 模块开启时调用此接口，展示"当前用的哪个 Vision 方案"。
    """
    from modules.core.ai_vision import get_vision_status
    config = request.app.state.config
    return get_vision_status(config)


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