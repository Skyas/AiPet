# Changelog

## [0.2.0] - 2026-03

### Added
- 设置面板新增 AI 服务商快速选择（OpenAI / Claude / Gemini / DeepSeek / Kimi / 智谱 / Ollama / LM Studio / 自定义）
- 生成参数新增 Top-P 滑块，附悬停说明文字
- 温度滑块补充范围说明

### Changed
- 聊天窗口和设置面板背景改为纯不透明 rgb()，透明度完全由 Electron 窗口 opacity 控制，100% = 完全不透明
- 清空对话按钮改为带文字的红色标签按钮，更醒目
- 路由跳转改用 replace 避免重复导航崩溃
- 后端 ai_chat 支持 top_p 参数透传

## [0.1.0] - 2026-03

### Added
- 前后端基础通信（REST + WebSocket/Socket.IO）
- 文本对话流式输出、SQLite 历史持久化
- 悬浮窗 UI（无边框、置顶、系统托盘、全局热键 Ctrl+Shift+A）
- 配置管理、模块开关框架、Prompt 编辑器
- Windows 一键启动脚本