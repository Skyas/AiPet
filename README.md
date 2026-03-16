# AiPet — AI 个人桌宠 🐾

> 运行在桌面的 AI 助手，支持文字对话、屏幕感知与游戏陪玩、语音交互（可选）、QQ 监听（可选）

**当前版本：** v0.3.0 (Phase 2 — 屏幕视觉与 AI 主动陪玩)

---

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- Windows 10/11

### 第一步：安装依赖

```bat
scripts\install.bat
```

### 第二步：配置 API Key

运行一次后，编辑 `backend/config/user_config.json`，或直接在 AiPet 设置面板里填写：

```json
{
  "ai": {
    "text_api_url": "https://api.openai.com/v1",
    "text_api_key": "sk-你的key",
    "text_model": "gpt-4o-mini"
  }
}
```

**如需使用视觉功能（屏幕感知 / 游戏陪玩）：**

- 若你的文本模型本身支持图片（gpt-4o、gemini、claude-3 等），无需额外配置，开启 Vision 模块即可。
- 若使用非多模态模型（如 DeepSeek），需前往设置面板填写**硅基流动 API Key**（免费注册：[siliconflow.cn](https://siliconflow.cn)），默认使用 `Qwen2.5-VL-7B-Instruct` 模型。

### 第三步：启动

```bat
scripts\start.bat
```

或开发模式（前后端热重载）：

```bat
scripts\dev.bat
```

---

## 项目结构

```
AiPet/
├── backend/                    # Python FastAPI 后端
│   ├── main.py                 # 启动入口
│   ├── api/                    # REST API 路由
│   │   ├── chat.py             # 对话（含视觉注入）
│   │   ├── screen.py           # 截图 / Vision / 主动引擎
│   │   └── settings_api.py     # 配置管理（含热重载）
│   ├── modules/
│   │   └── core/
│   │       ├── ai_chat.py          # 文本对话
│   │       ├── ai_vision.py        # 视觉分析（三档路由）
│   │       ├── screen_capture.py   # mss 截图
│   │       ├── vision_memory.py    # 屏幕滚动记忆
│   │       └── proactive_engine.py # AI 主动互动引擎
│   └── config/                 # 配置管理
├── frontend/                   # Electron + Vue 3 前端
│   ├── electron/               # 主进程
│   └── src/
│       ├── views/
│       │   ├── ChatPanel.vue       # 主对话界面
│       │   ├── VisionPanel.vue     # 游戏陪玩界面
│       │   ├── SettingsPanel.vue   # 设置面板
│       │   └── PromptEditor.vue    # Prompt 编辑器
│       └── utils/
│           ├── api.js              # API 封装
│           └── socket.js           # Socket.IO 单例
├── prompts/                    # Prompt 角色卡 (.json)
├── data/                       # 运行时数据库
└── scripts/                    # Windows 启动脚本
```

---

## 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 文字对话 | ✅ v0.1.0 | 流式输出，历史持久化 |
| Prompt 管理 | ✅ v0.1.0 | 角色卡创建 / 切换 |
| 屏幕感知 & 游戏陪玩 | ✅ v0.3.0 | 截图分析、对话注入、主动互动引擎 |
| 语音模块 | 🔜 Phase 3 | 可选，需额外安装依赖 |
| QQ 监听 | 🔜 Phase 4 | 可选，需安装 NapCat |

---

## 视觉功能说明

### Vision 路由优先级

| 优先级 | 条件 | 使用方案 |
|--------|------|----------|
| 1 | 文本模型为多模态（gpt-4o / gemini / claude-3 / qwen-vl 等） | 直接嵌图，无需额外配置 |
| 2 | 非多模态 + 已开启自定义 Vision 模型 | 用户自行配置的 Vision 端点 |
| 3 | 非多模态 + 未配置自定义 | 硅基流动 Qwen2.5-VL-7B-Instruct（免费） |

### 游戏陪玩面板

- **手动分析**：点击「分析当前画面」，AI 截图后发表评论
- **主动模式**：AI 定时观察屏幕，自主判断是否搭话（基于人设和画面变化）
- **对话注入**：开启后每次发消息自动截图，AI 能"看着屏幕"回答问题

### 主动互动机制

AI 不会无脑定时发言，而是通过返回 `[SILENT]` 自主决定是否开口。影响发言频率的因素：
- **人设**：话痨性格自然更频繁，内敛性格更安静
- **冷却机制**：用户主动发言后的一段时间内，AI 不打扰
- **变化检测**：画面无显著变化时倾向沉默，长时间无变化后会主动打破沉默

---

## 设置说明

### 配置热重载

修改设置后点击面板右上角「↺」按钮，配置立即对所有模块生效，**无需重启后端**。

### 语音模块（可选）

```bat
scripts\install_voice.bat
```

安装后在设置面板开启「语音模块」，重启后端生效。

---

## API 文档

后端启动后访问：http://localhost:8001/docs

---

## 版本记录

见 [CHANGELOG.md](CHANGELOG.md)