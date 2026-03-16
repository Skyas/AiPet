# Changelog

## [0.3.0] - 2026-03

### Added

**屏幕视觉与 AI 主动陪玩（Phase 2）**

- **截图模块**：基于 mss + Pillow 的高性能截图，支持多显示器选择配置
- **Vision 三档路由**：
  - 多模态文本模型（gpt-4o / gemini / claude-3 / qwen-vl 等）→ 直接嵌图，零额外 API 调用
  - 非多模态 + 已配置自定义 Vision 端点 → 使用用户配置
  - 非多模态 + 未配置 → 硅基流动 Qwen2.5-VL-7B-Instruct（免费）
- **对话视觉注入**：用户发消息时自动截图，将画面信息注入当前轮对话，AI 能"看着屏幕"回答
- **屏幕记忆**：VisionMemory 滚动缓冲区，记录最近 5 次屏幕观察，注入 system prompt 实现跨轮次时间连贯性
- **主动互动引擎**：ProactiveEngine 后台任务，AI 通过返回 `[SILENT]` 自主决定是否开口
  - 内置冷却检测：用户主动发言后一段时间内不打扰
  - 画面变化检测：无显著变化时倾向沉默（Jaccard 相似度）
  - 长时沉默强制触发：连续无变化超过阈值后主动打破沉默（"蹲了很久了"效果）
- **VisionPanel**：游戏陪玩专用界面，含实时观察流、手动触发、主动模式开关
- **Socket.IO 前端支持**：socket.js 全局单例，主动消息实时推送至 ChatPanel 和 VisionPanel
- **ChatPanel 主动消息展示**：AI 主动发言在对话流中以青色边框区分显示
- **配置热重载**：新增 `POST /api/settings/reload` 接口，设置面板「↺」按钮一键重载，无需重启后端

### Changed

- `chat.py`：用户发消息时并行执行截图和历史查询；视觉上下文注入对 AI 透明、对用户无感（历史记录仍为纯文本）
- `settings_api.py`：PUT 接口现在同步更新 vision_module 配置（修复之前漏更新导致改配置需重启的问题）
- `main.py`：服务启动时初始化 vision_module、vision_memory、proactive_engine；改用 lifespan 替代废弃的 `@app.on_event`
- `settings.py`：新增 `custom_vision_enabled`、`siliconflow_key` 字段；Vision 路由改为显式布尔开关控制，修复"改过再改回"路由混乱的问题
- `SettingsPanel.vue`：Vision 配置区块完全重设计，含当前路由状态指示器、硅基流动注册教程、自定义 Vision 模型配置界面

### Fixed

- Vision 路由错误：之前用字段值与默认值比对来判断"是否自定义"，导致填写后清空仍走自定义路由；现改为 `custom_vision_enabled` 显式开关
- `ai_vision.py` 硬编码 API Key 安全问题：移除硬编码 key，改为用户自行填写
- 非多模态模型未配置视觉 Key 时直接显示原始报错；现在给出有意义的提示和注册引导

---

## [0.2.0] - 2026-03

### Added
- 设置面板新增 AI 服务商快速选择（OpenAI / Claude / Gemini / DeepSeek / Kimi / 智谱 / Ollama / LM Studio / 自定义）
- 生成参数新增 Top-P 滑块，附悬停说明文字
- 温度滑块补充范围说明

### Changed
- 聊天窗口和设置面板背景改为纯不透明 rgb()，透明度完全由 Electron 窗口 opacity 控制
- 清空对话按钮改为带文字的红色标签按钮，更醒目
- 路由跳转改用 replace 避免重复导航崩溃
- 后端 ai_chat 支持 top_p 参数透传

---

## [0.1.0] - 2026-03

### Added
- 前后端基础通信（REST + WebSocket/Socket.IO）
- 文本对话流式输出、SQLite 历史持久化
- 悬浮窗 UI（无边框、置顶、系统托盘、全局热键 Ctrl+Shift+A）
- 配置管理、模块开关框架、Prompt 编辑器
- Windows 一键启动脚本