"""
主动互动引擎 — 自我判断式主动性（路由修正版）

视觉分析统一走 screen.py 的 get_screen_description()，
路由逻辑内聚在那里，不在这里重复。
"""
import asyncio
import time
from typing import Optional

_SILENT = "[SILENT]"
_FORCE_AFTER_SILENT = 4


class ProactiveEngine:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._app = None
        self._last_user_activity: float = 0.0
        self._last_proactive_time: float = 0.0
        self._consecutive_silent: int = 0

    def set_app(self, app):
        self._app = app

    def notify_user_activity(self):
        self._last_user_activity = time.time()

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        print("[ProactiveEngine] 主动互动引擎已启动")

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        print("[ProactiveEngine] 主动互动引擎已停止")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _loop(self):
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ProactiveEngine] _tick 异常（已忽略）: {e}")

            cfg      = self._get_vcfg()
            interval = max(15, cfg.get("proactive_check_interval", 45))
            await asyncio.sleep(interval)

    async def _tick(self):
        if not self._app:
            return

        vcfg = self._get_vcfg()

        # 1. 冷却检查
        user_cooldown = vcfg.get("proactive_user_cooldown", 60)
        if self._last_user_activity > 0 and \
                time.time() - self._last_user_activity < user_cooldown:
            return

        # 2. 最短主动间隔检查
        min_interval = vcfg.get("proactive_min_interval", 120)
        if self._last_proactive_time > 0 and \
                time.time() - self._last_proactive_time < min_interval:
            return

        # 3. 截图
        try:
            from modules.core.screen_capture import capture_screen
            region = vcfg.get("capture_region", "fullscreen")
            b64, _, _ = await asyncio.to_thread(capture_screen, region)
        except Exception as e:
            print(f"[ProactiveEngine] 截图失败: {e}")
            return

        # 4. 视觉分析 — 统一走 get_screen_description，路由逻辑内聚在那里
        try:
            from api.screen import get_screen_description
            vision_desc = await get_screen_description(self._app, b64)
        except Exception as e:
            print(f"[ProactiveEngine] 视觉分析失败: {e}")
            return

        # 5. 变化检测
        vision_memory = self._app.state.vision_memory
        has_change = vision_memory.has_significant_change(vision_desc)
        vision_memory.add(vision_desc, triggered_by="proactive")

        if not has_change:
            self._consecutive_silent += 1
            if self._consecutive_silent < _FORCE_AFTER_SILENT:
                return
        else:
            self._consecutive_silent = 0

        # 6. AI 自我判断
        reply = await self._ask_ai(vision_desc=vision_desc, b64=b64)
        if not reply or _SILENT in reply:
            return

        # 7. 推送并存档
        from modules.core.history import save_message
        session_id = vcfg.get("proactive_session_id", "default")
        save_message(session_id, "assistant", reply)

        latest_obs = vision_memory.get_latest()
        if latest_obs:
            latest_obs.associated_reply = reply

        await self._app.state.sio.emit("proactive_message", {
            "content":     reply,
            "vision_desc": vision_desc,
            "session_id":  session_id,
            "timestamp":   time.time(),
        })

        self._last_proactive_time = time.time()
        self._consecutive_silent  = 0
        print(f"[ProactiveEngine] 主动发言: {reply[:50]}...")

    async def _ask_ai(self, vision_desc: str, b64: str) -> Optional[str]:
        from modules.prompt_manager import get_prompt
        from modules.core.history import get_history
        from modules.core.ai_vision import get_vision_route, build_multimodal_user_message

        config         = self._app.state.config
        vcfg           = config.get("vision", {})
        active_id      = getattr(self._app.state, "active_prompt_id", "default_assistant")
        prompt_card    = get_prompt(active_id) or {}
        base_system    = prompt_card.get("system_prompt", "你是用户的 AI 桌宠。")
        session_id     = vcfg.get("proactive_session_id", "default")
        recent_history = get_history(session_id, limit=6)
        vision_memory  = self._app.state.vision_memory
        screen_history = vision_memory.get_context_for_prompt(n=3)

        system = f"""{base_system}

你现在处于「主动互动模式」。你会定期观察用户的屏幕，在合适的时机主动搭话。

【判断规则】
- 当前画面有趣、有值得评论的内容，或用户可能需要帮助 → 主动说话
- 画面没什么变化、用户在专注平静的事情（如听歌、阅读）→ 可以选择不打扰，但也不必完全沉默
- 如果你决定不说话，只回复：{_SILENT}（只有这四个字，不要加任何其他内容）
- 如果你决定说话，直接说出来，保持你的角色人设，简洁自然（50~100字）
- 不要解释"我决定说话/不说话"，直接给出结果"""

        parts = []
        if screen_history:
            parts.append(f"【最近屏幕变化记录】\n{screen_history}")
        parts.append(f"【当前屏幕画面】\n{vision_desc}")
        parts.append("请根据以上信息，决定是否要和用户说些什么。")
        user_text = "\n\n".join(parts)

        # multimodal 路由：直接嵌图，让 AI 亲眼看当前画面
        route = get_vision_route(config)
        if route == "multimodal":
            user_message = build_multimodal_user_message(user_text, b64)
        else:
            user_message = {"role": "user", "content": user_text}

        messages = list(recent_history) + [user_message]

        chat_module = self._app.state.chat_module
        try:
            reply = await chat_module.chat_once(messages, system_prompt=system)
            return reply.strip()
        except Exception as e:
            print(f"[ProactiveEngine] AI 自我判断调用失败: {e}")
            return None

    def _get_vcfg(self) -> dict:
        if not self._app:
            return {}
        return self._app.state.config.get("vision", {})