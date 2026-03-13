# AiPet — AI 个人桌宠 🐾

> 运行在桌面的 AI 助手，支持文字对话、屏幕感知（规划中）、语音交互（可选）、QQ 监听（可选）

**当前版本：** v0.1.0 (Phase 1 — 核心框架)

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

运行一次后，编辑 `backend/config/user_config.json`：

```json
{
  "ai": {
    "text_api_url": "https://api.openai.com/v1",
    "text_api_key": "sk-你的key",
    "text_model": "gpt-4o-mini"
  }
}
```

> 也可以直接在 AiPet 设置面板里填写，无需手动编辑文件。

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
├── backend/          # Python FastAPI 后端
│   ├── main.py       # 启动入口
│   ├── api/          # REST API 路由
│   ├── modules/      # 功能模块（core/voice/qq）
│   └── config/       # 配置管理
├── frontend/         # Electron + Vue 3 前端
│   ├── electron/     # 主进程
│   └── src/          # Vue 页面和逻辑
├── prompts/          # Prompt 角色卡 (.json)
├── data/             # 运行时数据库
└── scripts/          # Windows 启动脚本
```

---

## 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 文字对话 | ✅ Phase 1 | 流式输出，历史持久化 |
| Prompt 管理 | ✅ Phase 1 | 角色卡创建/切换 |
| 屏幕感知 | 🔜 Phase 3 | 截图 + Vision API |
| 语音模块 | 🔜 Phase 2 | 可选，需额外安装依赖 |
| QQ 监听 | 🔜 Phase 4 | 可选，需安装 NapCat |

### 语音模块（可选）

```bat
scripts\install_voice.bat
```

安装后在设置面板开启「语音模块」，重启后端生效。

---

## API 文档

后端启动后访问：http://localhost:8000/docs

---

## 版本记录

见 [CHANGELOG.md](CHANGELOG.md)
