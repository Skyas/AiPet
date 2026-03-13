<template>
    <div class="settings-panel">
        <div class="titlebar" style="-webkit-app-region: drag">
            <span class="title">⚙ 设置</span>
            <button class="icon-btn" style="-webkit-app-region: no-drag" @click="goBack">✕</button>
        </div>

        <div class="content">
            <!-- AI 模型 -->
            <section class="section">
                <div class="section-title">AI 模型</div>
                <label class="field">
                    <span>服务商</span>
                    <div class="provider-grid">
                        <button v-for="p in providers" :key="p.id"
                                class="provider-btn" :class="{ active: selectedProvider === p.id }"
                                @click="selectProvider(p)">
                            {{ p.name }}
                        </button>
                    </div>
                </label>
                <label class="field" v-if="selectedProvider === 'custom'">
                    <span>API 地址</span>
                    <input v-model="cfg.ai.text_api_url" @blur="save" placeholder="https://your-api.com/v1" />
                </label>
                <label class="field" v-else>
                    <span>API 地址</span>
                    <input :value="cfg.ai.text_api_url" readonly class="readonly" />
                </label>
                <label class="field">
                    <span>API Key</span>
                    <input v-model="cfg.ai.text_api_key" @blur="save" type="password" placeholder="sk-..." />
                </label>
                <label class="field">
                    <span>模型名称</span>
                    <input v-model="cfg.ai.text_model" @blur="save" :placeholder="currentProvider?.defaultModel || 'model-name'" />
                </label>
            </section>

            <!-- 生成参数 -->
            <section class="section">
                <div class="section-title">生成参数</div>
                <div class="param-row">
                    <div class="param-label">
                        <span>温度</span>
                        <span class="param-value">{{ cfg.ai.temperature }}</span>
                        <span class="param-hint" title="控制输出的随机程度。越高越有创意，越低越稳定保守。建议 0.5~1.2">?</span>
                    </div>
                    <input v-model.number="cfg.ai.temperature" @change="save" type="range" min="0" max="2" step="0.05" />
                    <div class="param-tips">稳定 (0) ←————→ 创意 (2)</div>
                </div>
                <div class="param-row">
                    <div class="param-label">
                        <span>Top-P</span>
                        <span class="param-value">{{ cfg.ai.top_p }}</span>
                        <span class="param-hint" title="核采样：从累计概率达到 P 的候选词中选取。通常与温度二选一调整，另一个保持默认即可">?</span>
                    </div>
                    <input v-model.number="cfg.ai.top_p" @change="save" type="range" min="0.01" max="1" step="0.01" />
                    <div class="param-tips">集中 (0.1) ←————→ 全量 (1.0)</div>
                </div>
            </section>

            <!-- 窗口 -->
            <section class="section">
                <div class="section-title">窗口</div>
                <div class="param-row">
                    <div class="param-label">
                        <span>透明度</span>
                        <span class="param-value">{{ Math.round(cfg.window.opacity * 100) }}%</span>
                    </div>
                    <input v-model.number="cfg.window.opacity" @change="applyOpacity" type="range" min="0.3" max="1" step="0.05" />
                    <div class="param-tips">半透明 (30%) ←————→ 不透明 (100%)</div>
                </div>
                <label class="field toggle">
                    <span>始终置顶</span>
                    <input type="checkbox" v-model="cfg.window.always_on_top" @change="save" />
                </label>
            </section>

            <!-- Prompt -->
            <section class="section">
                <div class="section-title">角色 Prompt</div>
                <button class="btn-secondary" @click="$router.replace('/prompts')">管理 Prompt 卡片 →</button>
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
                    <div class="module-status warn" v-if="cfg.voice.enabled">⚠ 重启后端后生效</div>
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
                    <div class="module-status warn" v-if="cfg.qq.enabled">⚠ 重启后端后生效</div>
                </div>
            </section>

            <div class="save-notice" v-if="saved">✅ 已保存</div>
        </div>
    </div>
</template>

<script setup>
    import { ref, computed, onMounted } from 'vue'
    import { useRouter } from 'vue-router'
    import { useSettingsStore } from '@/stores/settings'
    import { settingsAPI } from '@/utils/api'

    const router = useRouter()
    const settingsStore = useSettingsStore()
    const saved = ref(false)
    let saveTimer = null

    const cfg = ref({
        ai: { text_api_url: '', text_api_key: '', text_model: '', temperature: 0.8, top_p: 1.0 },
        voice: { enabled: false },
        qq: { enabled: false },
        window: { opacity: 0.95, always_on_top: true }
    })

    const providers = [
        { id: 'openai', name: 'OpenAI', url: 'https://api.openai.com/v1', defaultModel: 'gpt-4o-mini' },
        { id: 'claude', name: 'Claude', url: 'https://api.anthropic.com/v1', defaultModel: 'claude-3-5-haiku-20241022' },
        { id: 'gemini', name: 'Gemini', url: 'https://generativelanguage.googleapis.com/v1beta/openai/', defaultModel: 'gemini-2.0-flash' },
        { id: 'deepseek', name: 'DeepSeek', url: 'https://api.deepseek.com/v1', defaultModel: 'deepseek-chat' },
        { id: 'moonshot', name: 'Kimi', url: 'https://api.moonshot.cn/v1', defaultModel: 'moonshot-v1-8k' },
        { id: 'zhipu', name: '智谱', url: 'https://open.bigmodel.cn/api/paas/v4/', defaultModel: 'glm-4-flash' },
        { id: 'ollama', name: 'Ollama', url: 'http://localhost:11434/v1', defaultModel: 'llama3' },
        { id: 'lmstudio', name: 'LM Studio', url: 'http://localhost:1234/v1', defaultModel: 'local-model' },
        { id: 'custom', name: '自定义', url: '', defaultModel: '' },
    ]

    const selectedProvider = ref('custom')
    const currentProvider = computed(() => providers.find(p => p.id === selectedProvider.value))

    function detectProvider(url) {
        const match = providers.find(p => p.id !== 'custom' && p.url === url)
        return match ? match.id : 'custom'
    }

    function selectProvider(p) {
        selectedProvider.value = p.id
        if (p.id !== 'custom') {
            cfg.value.ai.text_api_url = p.url
            const isDefault = providers.some(pr => pr.defaultModel === cfg.value.ai.text_model)
            if (!cfg.value.ai.text_model || isDefault) cfg.value.ai.text_model = p.defaultModel
        }
        save()
    }

    function goBack() { router.replace('/') }

    onMounted(async () => {
        await settingsStore.load()
        if (settingsStore.config) {
            cfg.value = JSON.parse(JSON.stringify(settingsStore.config))
            if (cfg.value.ai.top_p === undefined) cfg.value.ai.top_p = 1.0
            selectedProvider.value = detectProvider(cfg.value.ai.text_api_url)
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
        saved.value = true; setTimeout(() => { saved.value = false }, 2000)
    }

    async function toggleQQ() {
        await settingsAPI.toggleQQ(cfg.value.qq.enabled)
        saved.value = true; setTimeout(() => { saved.value = false }, 2000)
    }

    function applyOpacity() {
        window.electronAPI?.setOpacity(cfg.value.window.opacity)
        save()
    }
</script>

<style scoped>
    .settings-panel {
        display: flex;
        flex-direction: column;
        height: 100vh;
        background: rgb(18, 18, 22);
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        color: #e8e8ec;
        font-family: system-ui, sans-serif;
        overflow: hidden;
    }

    .titlebar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        flex-shrink: 0;
    }

    .title {
        font-size: 14px;
        font-weight: 500;
        color: #c9b8f8;
    }

    .icon-btn {
        background: none;
        border: none;
        color: #888;
        font-size: 14px;
        padding: 3px 8px;
        border-radius: 6px;
        cursor: pointer;
    }

        .icon-btn:hover {
            background: rgba(255,255,255,0.08);
            color: #ddd;
        }

    .content {
        flex: 1;
        overflow-y: auto;
        padding: 12px 14px;
    }

        .content::-webkit-scrollbar {
            width: 4px;
        }

        .content::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
        }

    .section {
        margin-bottom: 20px;
    }

    .section-title {
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #555;
        margin-bottom: 10px;
    }

    .provider-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 5px;
        margin-top: 4px;
    }

    .provider-btn {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        color: #999;
        font-size: 11px;
        padding: 5px 4px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s;
    }

        .provider-btn:hover {
            background: rgba(255,255,255,0.08);
            color: #ccc;
        }

        .provider-btn.active {
            background: rgba(139,92,246,0.2);
            border-color: rgba(139,92,246,0.5);
            color: #c9b8f8;
            font-weight: 500;
        }

    .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: 10px;
    }

        .field > span {
            font-size: 12px;
            color: #888;
        }

        .field input[type="text"], .field input[type="password"] {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #e8e8ec;
            font-size: 12px;
            padding: 6px 10px;
            outline: none;
        }

            .field input[type="text"]:focus, .field input[type="password"]:focus {
                border-color: rgba(139,92,246,0.4);
            }

        .field input.readonly {
            color: #555;
            cursor: default;
        }

        .field.toggle {
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
        }

    .param-row {
        margin-bottom: 14px;
    }

    .param-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #888;
        margin-bottom: 5px;
    }

    .param-value {
        background: rgba(139,92,246,0.15);
        color: #c9b8f8;
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 4px;
        min-width: 32px;
        text-align: center;
    }

    .param-hint {
        width: 15px;
        height: 15px;
        border-radius: 50%;
        background: rgba(255,255,255,0.08);
        color: #666;
        font-size: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: help;
        flex-shrink: 0;
        margin-left: auto;
    }

        .param-hint:hover {
            background: rgba(139,92,246,0.2);
            color: #c9b8f8;
        }

    .param-row input[type="range"] {
        width: 100%;
        accent-color: #8b5cf6;
    }

    .param-tips {
        font-size: 10px;
        color: #444;
        margin-top: 3px;
    }

    .module-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 8px;
        transition: border-color 0.2s;
    }

        .module-card.active {
            border-color: rgba(139,92,246,0.3);
        }

    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }

        .module-header > span {
            font-size: 13px;
            font-weight: 500;
        }

    .module-desc {
        font-size: 11px;
        color: #555;
    }

    .module-status.warn {
        font-size: 11px;
        color: #facc15;
        margin-top: 4px;
    }

    .toggle-switch {
        position: relative;
        display: inline-block;
        width: 36px;
        height: 20px;
    }

        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

    .slider {
        position: absolute;
        cursor: pointer;
        inset: 0;
        background: rgba(255,255,255,0.1);
        border-radius: 20px;
        transition: 0.2s;
    }

        .slider:before {
            content: '';
            position: absolute;
            width: 14px;
            height: 14px;
            left: 3px;
            bottom: 3px;
            background: #888;
            border-radius: 50%;
            transition: 0.2s;
        }

    .toggle-switch input:checked + .slider {
        background: rgba(139,92,246,0.6);
    }

        .toggle-switch input:checked + .slider:before {
            transform: translateX(16px);
            background: #fff;
        }

    .btn-secondary {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        color: #c9b8f8;
        font-size: 12px;
        padding: 7px 12px;
        border-radius: 8px;
        cursor: pointer;
        width: 100%;
        text-align: left;
    }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.09);
        }

    .save-notice {
        text-align: center;
        font-size: 12px;
        color: #4ade80;
        padding: 8px;
    }
</style>