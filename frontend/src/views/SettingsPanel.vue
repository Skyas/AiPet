<template>
  <div class="settings-panel">
    <div class="titlebar" style="-webkit-app-region: drag">
      <span class="title">⚙ 设置</span>
      <button class="icon-btn" style="-webkit-app-region: no-drag" @click="goBack">✕</button>
    </div>

    <div class="content" v-if="settingsStore.loaded">
      <!-- AI 配置 -->
      <section class="section">
        <div class="section-title">AI 模型</div>
        <label class="field">
          <span>API 地址</span>
          <input v-model="cfg.ai.text_api_url" @blur="save" placeholder="https://api.openai.com/v1" />
        </label>
        <label class="field">
          <span>API Key</span>
          <input v-model="cfg.ai.text_api_key" @blur="save" type="password" placeholder="sk-..." />
        </label>
        <label class="field">
          <span>模型名称</span>
          <input v-model="cfg.ai.text_model" @blur="save" placeholder="gpt-4o-mini" />
        </label>
        <label class="field">
          <span>温度 ({{ cfg.ai.temperature }})</span>
          <input v-model.number="cfg.ai.temperature" @change="save" type="range" min="0" max="2" step="0.1" />
        </label>
      </section>

      <!-- 窗口设置 -->
      <section class="section">
        <div class="section-title">窗口</div>
        <label class="field">
          <span>透明度 ({{ Math.round(cfg.window.opacity * 100) }}%)</span>
          <input v-model.number="cfg.window.opacity" @change="applyOpacity" type="range" min="0.3" max="1" step="0.05" />
        </label>
        <label class="field toggle">
          <span>始终置顶</span>
          <input type="checkbox" v-model="cfg.window.always_on_top" @change="save" />
        </label>
      </section>

      <!-- Prompt 管理 -->
      <section class="section">
        <div class="section-title">角色 Prompt</div>
        <button class="btn-secondary" @click="$router.push('/prompts')">管理 Prompt 卡片 →</button>
      </section>

      <!-- 模块开关 -->
      <section class="section">
        <div class="section-title">功能模块</div>

        <div class="module-card" :class="{ active: cfg.voice.enabled }">
          <div class="module-header">
            <span>🎙 语音模块</span>
            <label class="toggle-switch">
              <input type="checkbox" v-model="cfg.voice.enabled" @change="toggleVoice" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="module-desc">唤醒词 / STT 识别 / TTS 合成（需安装额外依赖）</div>
          <div class="module-status" v-if="cfg.voice.enabled">
            ⚠ 重启后端后生效
          </div>
        </div>

        <div class="module-card" :class="{ active: cfg.qq.enabled }">
          <div class="module-header">
            <span>💬 QQ 模块</span>
            <label class="toggle-switch">
              <input type="checkbox" v-model="cfg.qq.enabled" @change="toggleQQ" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="module-desc">QQ 消息监听 / 通知（需安装 NapCat）</div>
          <div class="module-status" v-if="cfg.qq.enabled">
            ⚠ 重启后端后生效
          </div>
        </div>
      </section>

      <div class="save-notice" v-if="saved">✅ 已保存</div>
    </div>

    <div class="loading" v-else>加载配置中...</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { settingsAPI } from '@/utils/api'

const router = useRouter()
const settingsStore = useSettingsStore()
const saved = ref(false)
let saveTimer = null

// 初始化带完整默认结构，防止模板渲染时 undefined
const cfg = ref({
  ai: { text_api_url: '', text_api_key: '', text_model: '', temperature: 0.8 },
  voice: { enabled: false },
  qq: { enabled: false },
  window: { opacity: 0.95, always_on_top: true }
})

function goBack() {
  router.replace('/')
}

onMounted(async () => {
  await settingsStore.load()
  if (settingsStore.config) {
    cfg.value = JSON.parse(JSON.stringify(settingsStore.config))
  }
})

async function save() {
  await settingsStore.update(cfg.value)
  saved.value = true
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => { saved.value = false }, 2000)
}

async function toggleVoice() {
  await settingsAPI.toggleVoice(cfg.value.voice.enabled)
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

async function toggleQQ() {
  await settingsAPI.toggleQQ(cfg.value.qq.enabled)
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

function applyOpacity() {
  window.electronAPI?.setOpacity(cfg.value.window.opacity)
  save()
}
</script>

<style scoped>
.settings-panel {
  display: flex; flex-direction: column; height: 100vh;
  background: rgba(18, 18, 22, 0.95); backdrop-filter: blur(12px);
  border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);
  color: #e8e8ec; font-family: system-ui, sans-serif; overflow: hidden;
}
.titlebar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px 8px; border-bottom: 1px solid rgba(255,255,255,0.06);
}
.title { font-size: 14px; font-weight: 500; color: #c9b8f8; }
.icon-btn {
  background: none; border: none; color: #888; font-size: 14px;
  padding: 3px 8px; border-radius: 6px; cursor: pointer;
}
.icon-btn:hover { background: rgba(255,255,255,0.08); color: #ddd; }
.content { flex: 1; overflow-y: auto; padding: 12px; }
.content::-webkit-scrollbar { width: 4px; }
.content::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

.section { margin-bottom: 20px; }
.section-title {
  font-size: 11px; font-weight: 500; text-transform: uppercase;
  letter-spacing: 0.08em; color: #666; margin-bottom: 8px;
}
.field {
  display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px;
}
.field span { font-size: 12px; color: #aaa; }
.field input[type="text"],
.field input[type="password"],
.field input[type="number"] {
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; color: #e8e8ec; font-size: 12px; padding: 6px 10px;
  outline: none;
}
.field input[type="text"]:focus,
.field input[type="password"]:focus { border-color: rgba(139,92,246,0.4); }
.field input[type="range"] { width: 100%; accent-color: #8b5cf6; }
.field.toggle { flex-direction: row; align-items: center; justify-content: space-between; }

.module-card {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px; padding: 10px 12px; margin-bottom: 8px;
  transition: border-color 0.2s;
}
.module-card.active { border-color: rgba(139,92,246,0.3); }
.module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.module-header span { font-size: 13px; font-weight: 500; }
.module-desc { font-size: 11px; color: #666; }
.module-status { font-size: 11px; color: #facc15; margin-top: 4px; }

/* Toggle switch */
.toggle-switch { position: relative; display: inline-block; width: 36px; height: 20px; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute; cursor: pointer; inset: 0;
  background: rgba(255,255,255,0.1); border-radius: 20px; transition: 0.2s;
}
.slider:before {
  content: ''; position: absolute; width: 14px; height: 14px;
  left: 3px; bottom: 3px; background: #888; border-radius: 50%; transition: 0.2s;
}
.toggle-switch input:checked + .slider { background: rgba(139,92,246,0.6); }
.toggle-switch input:checked + .slider:before { transform: translateX(16px); background: #fff; }

.btn-secondary {
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  color: #c9b8f8; font-size: 12px; padding: 7px 12px; border-radius: 8px;
  cursor: pointer; width: 100%; text-align: left;
}
.btn-secondary:hover { background: rgba(255,255,255,0.09); }

.save-notice {
  text-align: center; font-size: 12px; color: #4ade80;
  padding: 8px; margin-top: 4px;
}
.loading { display: flex; align-items: center; justify-content: center; flex: 1; color: #555; }
</style>
