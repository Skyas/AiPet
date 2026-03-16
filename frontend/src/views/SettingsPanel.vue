<template>
    <div class="settings-panel">
        <!-- ── 标题栏（含内联 toast）─────────────────────────────────────────── -->
        <div class="titlebar" style="-webkit-app-region: drag">
            <span class="title">⚙ 设置</span>
            <div style="-webkit-app-region: no-drag; display:flex; align-items:center; gap:6px">
                <transition name="toast">
                    <span v-if="saved" class="reload-status" :class="savedOk ? 'rstat-ok' : 'rstat-err'">
                        {{ savedMsg }}
                    </span>
                </transition>
                <button class="icon-btn reload-btn" @click="reloadConfig"
                        :title="'重载配置（无需重启后端）'"
                        :class="{ spinning: reloading }">↺</button>
                <button class="icon-btn" @click="goBack">✕</button>
            </div>
        </div>

        <div class="content">

            <!-- ═══════════════ AI 模型 ═══════════════ -->
            <section class="section">
                <div class="section-title">AI 模型</div>

                <!-- 服务商选择（绿点 = 已配置 Key） -->
                <label class="field">
                    <span>服务商</span>
                    <div class="provider-grid">
                        <button v-for="(pc, pid) in PROVIDER_CONFIGS" :key="pid"
                                class="provider-btn"
                                :class="{ active: cfg.ai.active_provider === pid }"
                                @click="selectProvider(pid)">
                            {{ pc.name }}
                            <span class="key-dot" :class="hasProviderKey(pid) ? 'dot-ok' : 'dot-empty'"></span>
                        </button>
                    </div>
                </label>

                <!-- API 地址（custom 可编辑，其余只读） -->
                <label class="field">
                    <span>API 地址</span>
                    <input v-if="cfg.ai.active_provider === 'custom'"
                           v-model="cfg.ai.text_api_url"
                           @blur="onCustomUrlBlur"
                           placeholder="https://your-api.com/v1" />
                    <input v-else :value="cfg.ai.text_api_url" readonly class="readonly" />
                </label>

                <!-- API Key（带状态徽章） -->
                <label class="field">
                    <span>
                        API Key
                        <span v-if="isLocalProvider" class="hint-inline">（本地服务无需 Key）</span>
                    </span>
                    <div class="key-row">
                        <input v-model="currentProviderKey"
                               @blur="save"
                               type="password"
                               :placeholder="currentProviderConfig?.keyPlaceholder || 'sk-...'"
                               :readonly="!!currentProviderConfig?.fixedKey"
                               :class="{ readonly: !!currentProviderConfig?.fixedKey }" />
                        <span v-if="currentProviderKey && !currentProviderConfig?.fixedKey"
                              class="key-badge key-ok" title="Key 已配置">✓</span>
                        <span v-else-if="!currentProviderKey && !isLocalProvider"
                              class="key-badge key-warn" title="尚未填写 Key">!</span>
                    </div>
                </label>

                <!-- 模型（预设按钮 + 自定义按钮） -->
                <label class="field">
                    <span>模型</span>
                    <div class="model-presets">
                        <button v-for="m in currentProviderConfig.models" :key="m.id"
                                class="model-preset-btn"
                                :class="{ active: cfg.ai.text_model === m.id && !isCustomModel }"
                                @click="selectModel(m.id)">
                            {{ m.label }}
                        </button>
                        <button class="model-preset-btn model-custom-btn"
                                :class="{ active: isCustomModel }"
                                @click="enableCustomModel">
                            自定义
                        </button>
                    </div>
                    <!-- 自定义输入框：仅在选中「自定义」时显示 -->
                    <input v-if="isCustomModel"
                           v-model="cfg.ai.text_model"
                           @blur="saveModel"
                           placeholder="输入完整模型名称"
                           ref="customModelInput" />
                    <!-- 预设时只读展示当前模型名 -->
                    <input v-else :value="cfg.ai.text_model" readonly class="readonly" />
                </label>
            </section>

            <!-- ═══════════════ 生成参数 ═══════════════ -->
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
                        <span class="param-hint" title="核采样。通常与温度二选一调整。">?</span>
                    </div>
                    <input v-model.number="cfg.ai.top_p" @change="save" type="range" min="0.01" max="1" step="0.01" />
                    <div class="param-tips">集中 (0.1) ←————→ 全量 (1.0)</div>
                </div>
            </section>

            <!-- ═══════════════ 窗口 ═══════════════ -->
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
                    <input type="checkbox" v-model="cfg.window.always_on_top" @change="applyAlwaysOnTop" />
                </label>
            </section>

            <!-- ═══════════════ Prompt ═══════════════ -->
            <section class="section">
                <div class="section-title">角色 Prompt</div>
                <button class="btn-secondary" @click="$router.replace('/prompts')">管理 Prompt 卡片 →</button>
            </section>

            <!-- ═══════════════ 视觉陪玩 ═══════════════ -->
            <section class="section">
                <div class="section-title">视觉陪玩</div>

                <!-- 总开关 -->
                <div class="module-card" :class="{ active: cfg.vision?.enabled }">
                    <div class="module-header">
                        <span>👁 Vision 模块</span>
                        <label class="toggle-switch">
                            <input type="checkbox" v-model="cfg.vision.enabled" @change="save" />
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="module-desc">截图分析 · 对话注入 · AI 主动陪玩</div>
                </div>

                <div v-if="cfg.vision?.enabled" class="vision-config">

                    <!-- 当前视觉方案指示器 -->
                    <div class="route-indicator" :class="routeClass">
                        <span class="route-icon">{{ routeIcon }}</span>
                        <div class="route-info">
                            <div class="route-label">{{ routeLabel }}</div>
                            <div class="route-sub" v-if="routeWarning" style="color:#f59e0b">⚠ {{ routeWarning }}</div>
                        </div>
                    </div>

                    <!-- 视觉模型配置 -->
                    <div class="sub-title">视觉模型</div>

                    <!-- 情况A：多模态文本模型，无需额外配置 -->
                    <div v-if="visionRoute === 'multimodal'" class="info-box info-ok">
                        ✓ 你的 AI 模型（{{ cfg.ai.text_model }}）原生支持图片分析，无需单独配置视觉模型。
                    </div>

                    <!-- 情况B/C：非多模态 -->
                    <div v-else>
                        <!-- B：硅基流动默认 -->
                        <div v-if="!cfg.vision.custom_vision_enabled">
                            <div class="info-box info-neutral">
                                使用默认视觉模型：<strong>GLM-4.1V-9B-Thinking</strong>（硅基流动免费提供）
                            </div>
                            <label class="field">
                                <span>
                                    硅基流动 API Key
                                    <span class="hint-inline required">（必填）</span>
                                </span>
                                <input v-model="cfg.vision.siliconflow_key" @blur="save"
                                       type="password" placeholder="sk-..." />
                            </label>
                            <div v-if="!cfg.vision.siliconflow_key?.trim()" class="warn-box">
                                <div class="warn-title">⚠ 未填写 Key，视觉功能暂不可用</div>
                                <div class="guide-toggle" @click="showSfGuide = !showSfGuide">
                                    {{ showSfGuide ? '▲ 收起教程' : '▼ 展开注册教程（免费，2分钟）' }}
                                </div>
                                <div v-if="showSfGuide" class="guide-body">
                                    <div class="guide-step">
                                        <span class="step-num">1</span>
                                        <span>打开 <strong>siliconflow.cn</strong>，点击右上角「注册」，用手机号或邮箱注册账号（完全免费）</span>
                                    </div>
                                    <div class="guide-step">
                                        <span class="step-num">2</span>
                                        <span>登录后进入「控制台」→ 左侧菜单找「API 密钥」→ 点「新建 API 密钥」</span>
                                    </div>
                                    <div class="guide-step">
                                        <span class="step-num">3</span>
                                        <span>复制生成的密钥（格式为 <code>sk-xxx...</code>），粘贴到上方输入框，点击输入框外部保存</span>
                                    </div>
                                    <div class="guide-step">
                                        <span class="step-num">4</span>
                                        <span><strong>GLM-4.1V-9B-Thinking</strong> 模型完全免费，无需充值，每天有足够的免费额度</span>
                                    </div>
                                    <div class="guide-note">
                                        💡 填好 Key 后，点击右上角「↺ 重载配置」按钮让后端立即生效，无需重启。
                                    </div>
                                </div>
                            </div>
                            <div v-else class="ok-box">✓ 硅基流动 Key 已配置</div>
                        </div>

                        <!-- C：自定义 Vision -->
                        <div v-if="cfg.vision.custom_vision_enabled">
                            <label class="field">
                                <span>Vision 服务商</span>
                                <div class="provider-grid">
                                    <button v-for="p in visionProviders" :key="p.id"
                                            class="provider-btn" :class="{ active: selectedVisionProvider === p.id }"
                                            @click="selectVisionProvider(p)">
                                        {{ p.name }}
                                    </button>
                                </div>
                            </label>
                            <label class="field" v-if="selectedVisionProvider === 'custom'">
                                <span>Vision API 地址</span>
                                <input v-model="cfg.vision.api_url" @blur="save"
                                       placeholder="https://your-vision-api.com/v1" />
                            </label>
                            <label class="field" v-else>
                                <span>Vision API 地址</span>
                                <input :value="cfg.vision.api_url" readonly class="readonly" />
                            </label>
                            <label class="field">
                                <span>
                                    Vision API Key
                                    <span class="hint-inline">（留空则复用 AI 模型 Key，仅同服务商时有效）</span>
                                </span>
                                <input v-model="cfg.vision.api_key" @blur="save"
                                       type="password" placeholder="留空则复用 AI 模型 Key" />
                            </label>
                            <label class="field">
                                <span>Vision 模型名</span>
                                <input v-model="cfg.vision.model" @blur="save"
                                       :placeholder="currentVisionProvider?.defaultModel || 'model-name'" />
                            </label>
                        </div>

                        <!-- 自定义开关 -->
                        <label class="field toggle" style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.05)">
                            <span>
                                使用自定义 Vision 模型
                                <span class="hint-inline">（关闭则使用硅基流动默认）</span>
                            </span>
                            <input type="checkbox" v-model="cfg.vision.custom_vision_enabled" @change="save" />
                        </label>
                    </div>

                    <!-- 行为设置 -->
                    <div class="sub-title" style="margin-top:10px">行为设置</div>

                    <label class="field toggle">
                        <span>
                            对话时自动注入画面
                            <span class="hint-inline">（每次发消息都截图分析）</span>
                        </span>
                        <input type="checkbox" v-model="cfg.vision.inject_on_chat" @change="save" />
                    </label>

                    <label class="field">
                        <span>截图区域</span>
                        <select v-model="cfg.vision.capture_region" @change="save" class="select-input">
                            <option value="fullscreen">主显示器（全屏）</option>
                            <option v-for="m in monitors" :key="m.index" :value="`monitor:${m.index}`">
                                {{ m.label }}
                            </option>
                        </select>
                    </label>

                    <!-- AI 主动互动 -->
                    <div class="sub-title" style="margin-top:10px">AI 主动互动</div>

                    <div class="module-card" :class="{ active: cfg.vision.proactive_enabled }">
                        <div class="module-header">
                            <span>🤖 主动互动引擎</span>
                            <label class="toggle-switch">
                                <input type="checkbox" v-model="cfg.vision.proactive_enabled"
                                       @change="toggleProactive" />
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="module-desc">AI 定时观察屏幕，自主决定是否主动搭话</div>
                    </div>

                    <div v-if="cfg.vision.proactive_enabled">
                        <div class="param-row">
                            <div class="param-label">
                                <span>检查间隔</span>
                                <span class="param-value">{{ cfg.vision.proactive_check_interval }}s</span>
                                <span class="param-hint" title="AI 每隔多少秒检查一次是否要主动说话">?</span>
                            </div>
                            <input v-model.number="cfg.vision.proactive_check_interval" @change="save"
                                   type="range" min="15" max="180" step="5" />
                            <div class="param-tips">15s（活跃）←————→ 180s（安静）</div>
                        </div>
                        <div class="param-row">
                            <div class="param-label">
                                <span>用户冷却时间</span>
                                <span class="param-value">{{ cfg.vision.proactive_user_cooldown }}s</span>
                                <span class="param-hint" title="用户发消息后，AI 在这段时间内不主动打扰">?</span>
                            </div>
                            <input v-model.number="cfg.vision.proactive_user_cooldown" @change="save"
                                   type="range" min="30" max="300" step="10" />
                            <div class="param-tips">30s ←————→ 300s</div>
                        </div>
                    </div>

                    <button class="btn-secondary" style="margin-top:10px"
                            @click="$router.replace('/vision')">
                        打开游戏陪玩面板 →
                    </button>
                </div>
            </section>

            <!-- ═══════════════ 功能模块 ═══════════════ -->
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

        </div>
    </div>
</template>

<script setup>
    import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
    import { useRouter } from 'vue-router'
    import { useSettingsStore } from '@/stores/settings'
    import { settingsAPI, screenAPI } from '@/utils/api'

    const router = useRouter()
    const settingsStore = useSettingsStore()

    const saved = ref(false)
    const savedOk = ref(true)
    const savedMsg = ref('✅ 已保存')
    const reloading = ref(false)
    const blockSave = ref(false)  // reload 期间屏蔽 save
    const isDirty   = ref(false)   // 用户是否有过实际改动
    const monitors = ref([])
    const showSfGuide = ref(false)
    const selectedVisionProvider = ref('custom')
    const isCustomModel = ref(false)  // 是否处于自定义模型输入模式
    const customModelInput = ref(null)
    let saveTimer = null

    // ── 各厂商静态配置 ────────────────────────────────────────────────────────
    // models 数组：id = 实际传给 API 的模型名，label = 界面显示文字
    // fixedKey = 本地服务填固定占位值（不让用户乱改）
    const PROVIDER_CONFIGS = {
        openai: {
            name: 'OpenAI',
            url: 'https://api.openai.com/v1',
            models: [
                { id: 'gpt-4o-mini', label: '4o Mini（快速）' },
                { id: 'gpt-4o',      label: '4o（强力）' },
            ],
            keyPlaceholder: 'sk-...',
        },
        deepseek: {
            name: 'DeepSeek',
            url: 'https://api.deepseek.com/v1',
            models: [
                { id: 'deepseek-chat',     label: 'V3 Chat（对话）' },
                { id: 'deepseek-reasoner', label: 'R1（推理）' },
            ],
            keyPlaceholder: 'sk-...',
        },
        gemini: {
            name: 'Gemini',
            url: 'https://generativelanguage.googleapis.com/v1beta/openai/',
            models: [
                { id: 'gemini-2.5-flash', label: 'Flash 2.5（快速）' },
                { id: 'gemini-2.5-pro',   label: 'Pro 2.5（强力）' },
            ],
            keyPlaceholder: 'AIzaSy...',
        },
        claude: {
            name: 'Claude',
            url: 'https://api.anthropic.com/v1',
            models: [
                { id: 'claude-3-5-haiku-20241022', label: 'Haiku 3.5（快速）' },
                { id: 'claude-sonnet-4-20250514',  label: 'Sonnet 4（强力）' },
            ],
            keyPlaceholder: 'sk-ant-...',
        },
        moonshot: {
            name: 'Kimi',
            url: 'https://api.moonshot.cn/v1',
            models: [
                { id: 'moonshot-v1-8k',  label: 'v1-8k（均衡）' },
                { id: 'moonshot-v1-32k', label: 'v1-32k（长文）' },
            ],
            keyPlaceholder: 'sk-...',
        },
        zhipu: {
            name: '智谱',
            url: 'https://open.bigmodel.cn/api/paas/v4/',
            models: [
                { id: 'glm-4-flash', label: 'GLM-4 Flash（免费）' },
                { id: 'glm-4-air',   label: 'GLM-4 Air（均衡）' },
            ],
            keyPlaceholder: '...',
        },
        siliconflow: {
            name: '硅基流动',
            url: 'https://api.siliconflow.cn/v1',
            models: [
                { id: 'deepseek-ai/DeepSeek-V3',       label: 'DeepSeek V3' },
                { id: 'Qwen/Qwen2.5-7B-Instruct',      label: 'Qwen2.5 7B（免费）' },
            ],
            keyPlaceholder: 'sk-...',
        },
        doubao: {
            name: '豆包',
            url: 'https://ark.cn-beijing.volces.com/api/v3/responses',
            models: [
                { id: 'doubao-seed-2-0-pro-260215',  label: 'Seed 2.0 Pro' },
                { id: 'doubao-seed-2-0-lite-260215', label: 'Seed 2.0 Lite' },
            ],
            keyPlaceholder: '火山引擎 API Key',
        },
        qwen: {
            name: '千问',
            url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            models: [
                { id: 'qwen3.5-plus',  label: 'Qwen3.5 Plus（均衡）' },
                { id: 'qwen3.5-flash', label: 'Qwen3.5 Flash（快速）' },
            ],
            keyPlaceholder: 'sk-...',
        },
        ollama: {
            name: 'Ollama',
            url: 'http://localhost:11434/v1',
            models: [
                { id: 'qwen2.5:7b',   label: 'Qwen2.5 7B' },
                { id: 'llama3.2:3b',  label: 'Llama3.2 3B' },
            ],
            keyPlaceholder: 'ollama',
            fixedKey: 'ollama',   // 本地服务填固定占位，后端需要非空值
        },
        lmstudio: {
            name: 'LM Studio',
            url: 'http://localhost:1234/v1',
            models: [
                { id: 'local-model', label: '已加载的本地模型' },
            ],
            keyPlaceholder: 'lm-studio',
            fixedKey: 'lm-studio',
        },
        custom: {
            name: '自定义',
            url: '',
            models: [],
            keyPlaceholder: 'sk-...',
        },
    }

    // ── Vision 服务商（不变）────────────────────────────────────────────────
    const visionProviders = [
        { id: 'openai',       name: 'OpenAI',    url: 'https://api.openai.com/v1',                                    defaultModel: 'gpt-4o' },
        { id: 'gemini',       name: 'Gemini',    url: 'https://generativelanguage.googleapis.com/v1beta/openai/',      defaultModel: 'gemini-2.0-flash' },
        { id: 'qwen',         name: '通义千问',  url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',            defaultModel: 'qwen-vl-max' },
        { id: 'zhipu',        name: '智谱',      url: 'https://open.bigmodel.cn/api/paas/v4/',                        defaultModel: 'glm-4v-flash' },
        { id: 'siliconflow',  name: '硅基流动',  url: 'https://api.siliconflow.cn/v1',                               defaultModel: 'Qwen/Qwen2.5-VL-7B-Instruct' },
        { id: 'ollama',       name: 'Ollama',    url: 'http://localhost:11434/v1',                                    defaultModel: 'llava' },
        { id: 'custom',       name: '自定义',    url: '',                                                              defaultModel: '' },
    ]

    // ── cfg 响应式对象 ────────────────────────────────────────────────────────
    const cfg = ref({
        ai: {
            active_provider: 'custom',
            text_api_url: '',
            text_api_key: '',
            text_model: '',
            temperature: 0.8,
            top_p: 1.0,
            providers: {},
        },
        voice: { enabled: false },
        qq: { enabled: false },
        window: { opacity: 0.95, always_on_top: true },
        vision: {
            enabled: false,
            custom_vision_enabled: false,
            siliconflow_key: '',
            inject_on_chat: true,
            proactive_enabled: false,
            proactive_check_interval: 45,
            proactive_user_cooldown: 60,
            api_url: '',
            api_key: '',
            model: '',
            capture_region: 'fullscreen',
        },
    })

    // ── 当前厂商配置 ───────────────────────────────────────────────────────────
    const currentProviderConfig = computed(() =>
        PROVIDER_CONFIGS[cfg.value.ai?.active_provider] ?? PROVIDER_CONFIGS.custom
    )

    // 本地服务（不需要 Key）
    const isLocalProvider = computed(() =>
        ['ollama', 'lmstudio'].includes(cfg.value.ai?.active_provider)
    )

    // 当前厂商 Key — computed 双向绑定，自动同步 providers 存储 + 扁平字段
    const currentProviderKey = computed({
        get() {
            const pid = cfg.value.ai?.active_provider || 'custom'
            const pc = PROVIDER_CONFIGS[pid]
            if (pc?.fixedKey) return pc.fixedKey
            return cfg.value.ai?.providers?.[pid]?.api_key || ''
        },
        set(val) {
            const pid = cfg.value.ai?.active_provider || 'custom'
            ensureProviderEntry(pid)
            cfg.value.ai.providers[pid].api_key = val
            cfg.value.ai.text_api_key = val   // 同步扁平字段（后端读这个）
        },
    })

    // 某厂商是否已填写 Key（用于服务商按钮上的绿点）
    function hasProviderKey(pid) {
        if (['ollama', 'lmstudio'].includes(pid)) return true
        return !!(cfg.value.ai?.providers?.[pid]?.api_key)
    }

    // 确保 providers[pid] 存在
    function ensureProviderEntry(pid) {
        if (!cfg.value.ai.providers) cfg.value.ai.providers = {}
        if (!cfg.value.ai.providers[pid]) cfg.value.ai.providers[pid] = { api_key: '', model: '' }
    }

    // ── 服务商选择 ────────────────────────────────────────────────────────────
    function selectProvider(pid) {
        const pc = PROVIDER_CONFIGS[pid]
        cfg.value.ai.active_provider = pid

        // 更新 URL（custom 保留用户填的）
        if (pid === 'custom') {
            cfg.value.ai.text_api_url = cfg.value.ai.providers?.custom?.url || ''
        } else {
            cfg.value.ai.text_api_url = pc.url
        }

        // 恢复该厂商存储的 Key
        const storedKey = cfg.value.ai.providers?.[pid]?.api_key || pc.fixedKey || ''
        cfg.value.ai.text_api_key = storedKey

        // 恢复该厂商存储的模型，没有则用第一个预设
        const storedModel = cfg.value.ai.providers?.[pid]?.model
        const isPreset = pc.models?.some(m => m.id === storedModel)
        if (storedModel && isPreset) {
            cfg.value.ai.text_model = storedModel
            isCustomModel.value = false
        } else if (storedModel) {
            // 存储的是自定义模型名
            cfg.value.ai.text_model = storedModel
            isCustomModel.value = true
        } else if (pc.models?.length) {
            cfg.value.ai.text_model = pc.models[0].id
            isCustomModel.value = false
        }

        silentSave()
    }

    // ── 模型选择 ──────────────────────────────────────────────────────────────
    function selectModel(modelId) {
        isCustomModel.value = false
        cfg.value.ai.text_model = modelId
        const pid = cfg.value.ai.active_provider
        ensureProviderEntry(pid)
        cfg.value.ai.providers[pid].model = modelId
        silentSave()
    }

    // 切换到「自定义」输入模式
    function enableCustomModel() {
        isCustomModel.value = true
        // 清空预设模型，让用户重新输入
        cfg.value.ai.text_model = ''
        nextTick(() => customModelInput.value?.focus())
    }

    // 输入框失焦时也同步存储该厂商的模型
    function saveModel() {
        const pid = cfg.value.ai.active_provider
        ensureProviderEntry(pid)
        cfg.value.ai.providers[pid].model = cfg.value.ai.text_model
        save()
    }

    // custom 的 URL 变化时同步存储
    function onCustomUrlBlur() {
        ensureProviderEntry('custom')
        cfg.value.ai.providers.custom.url = cfg.value.ai.text_api_url
        save()
    }

    // ── Vision 服务商 ─────────────────────────────────────────────────────────
    const currentVisionProvider = computed(() =>
        visionProviders.find(p => p.id === selectedVisionProvider.value)
    )

    function detectVisionProvider(url) {
        return visionProviders.find(p => p.id !== 'custom' && p.url === url)?.id ?? 'custom'
    }

    function selectVisionProvider(p) {
        selectedVisionProvider.value = p.id
        if (p.id !== 'custom') {
            cfg.value.vision.api_url = p.url
            const isDefault = visionProviders.some(pr => pr.defaultModel === cfg.value.vision.model)
            if (!cfg.value.vision.model || isDefault) cfg.value.vision.model = p.defaultModel
        }
        silentSave()
    }

    // ── 视觉路由状态 ──────────────────────────────────────────────────────────
    const MULTIMODAL_PATTERNS = [
        'gpt-4o', 'gpt-4-turbo', 'gpt-4-vision', 'claude-3', 'claude-sonnet',
        'claude-opus', 'claude-haiku', 'gemini', 'qwen-vl', 'qwen2-vl', 'qwenvl',
        'glm-4v', 'llava', 'internvl', 'deepseek-vl', 'minicpm-v', 'vision', 'multimodal',
    ]

    const visionRoute = computed(() => {
        const model = (cfg.value.ai?.text_model || '').toLowerCase()
        if (MULTIMODAL_PATTERNS.some(p => model.includes(p))) return 'multimodal'
        if (cfg.value.vision?.custom_vision_enabled) return 'custom'
        return 'default'
    })

    const routeLabel = computed(() => {
        if (visionRoute.value === 'multimodal') return `直接使用 ${cfg.value.ai.text_model} 分析图片`
        if (visionRoute.value === 'custom')     return `自定义：${cfg.value.vision.model || '未指定模型'}`
        return '硅基流动 GLM-4.1V-9B-Thinking（免费）'
    })

    const routeWarning = computed(() => {
        if (visionRoute.value === 'multimodal') return null
        if (visionRoute.value === 'custom') {
            return (cfg.value.vision.api_key || cfg.value.ai.text_api_key) ? null : 'Vision API Key 未填写'
        }
        return cfg.value.vision.siliconflow_key?.trim() ? null : '需要填写硅基流动 API Key'
    })

    const routeClass  = computed(() => ({ 'route-ok': !routeWarning.value, 'route-warn': !!routeWarning.value }))
    const routeIcon   = computed(() => visionRoute.value === 'multimodal' ? '🔀' : visionRoute.value === 'custom' ? '🔧' : '🆓')

    // ── 实时同步 model 到 providers（防止 selectProvider 读到旧值）──────────
    // 用户每次输入时立即写入 providers[pid].model，
    // 这样无论何时 selectProvider 被调用，storedModel 都是最新值
    watch(() => cfg.value.ai?.text_model, (newModel) => {
        const pid = cfg.value.ai?.active_provider
        if (!pid || newModel === undefined) return
        ensureProviderEntry(pid)
        cfg.value.ai.providers[pid].model = newModel
    })

    // ── 生命周期 ──────────────────────────────────────────────────────────────
    onMounted(async () => {
        await settingsStore.load()
        if (settingsStore.config) {
            cfg.value = JSON.parse(JSON.stringify(settingsStore.config))

            // 兼容旧配置：补全缺少的字段
            if (cfg.value.ai.top_p === undefined)  cfg.value.ai.top_p = 1.0
            if (!cfg.value.ai.providers)           cfg.value.ai.providers = {}
            if (!cfg.value.ai.active_provider) {
                // 根据当前 URL 反推厂商 ID
                cfg.value.ai.active_provider = detectProviderByUrl(cfg.value.ai.text_api_url)
            }

            // 迁移：把已有 text_api_key 写入对应厂商的 providers 存储
            const pid = cfg.value.ai.active_provider
            if (pid && cfg.value.ai.text_api_key && !cfg.value.ai.providers[pid]?.api_key) {
                ensureProviderEntry(pid)
                cfg.value.ai.providers[pid].api_key = cfg.value.ai.text_api_key
                cfg.value.ai.providers[pid].model   = cfg.value.ai.text_model
            }

            if (!cfg.value.vision)                              cfg.value.vision = {}
            if (cfg.value.vision.siliconflow_key === undefined) cfg.value.vision.siliconflow_key = ''
            if (cfg.value.vision.custom_vision_enabled === undefined) cfg.value.vision.custom_vision_enabled = false

            selectedVisionProvider.value = detectVisionProvider(cfg.value.vision.api_url || '')
        }

        isDirty.value = false
        try {
            const { monitors: ms } = await screenAPI.getMonitors()
            monitors.value = ms || []
        } catch { }
    })

    function detectProviderByUrl(url) {
        if (!url) return 'custom'
        for (const [pid, pc] of Object.entries(PROVIDER_CONFIGS)) {
            if (pid !== 'custom' && pc.url && url.startsWith(pc.url)) return pid
        }
        return 'custom'
    }

    // ── 保存 / 重载 ──────────────────────────────────────────────────────────
    async function silentSave() {
        if (blockSave.value) return
        isDirty.value = true
        await settingsStore.update(cfg.value)
    }

    async function save() {
        if (blockSave.value) return
        isDirty.value = true
        await settingsStore.update(cfg.value)
        flash('✅ 已保存', true)
    }

    async function reloadConfig() {
        reloading.value = true
        blockSave.value = true
        try {
            const res = await settingsAPI.reload()
            if (res.data?.ok) {
                await settingsStore.load()
                const fresh = JSON.parse(JSON.stringify(settingsStore.config))
                // 补全 providers（防止后端返回的旧格式没有该字段）
                if (!fresh.ai.providers) fresh.ai.providers = {}
                cfg.value = fresh
                selectedVisionProvider.value = detectVisionProvider(cfg.value.vision?.api_url || '')
                isDirty.value = false
                flash('✅ 配置已重载', true)
            }
        } catch {
            flash('❌ 重载失败，请检查后端是否运行', false)
        } finally {
            reloading.value = false
            blockSave.value = false
        }
    }

    function flash(msg, ok = true) {
        savedMsg.value = msg
        savedOk.value  = ok
        saved.value    = true
        clearTimeout(saveTimer)
        saveTimer = setTimeout(() => { saved.value = false }, 2500)
    }

    // ── 模块操作 ──────────────────────────────────────────────────────────────
    async function toggleProactive() {
        if (cfg.value.vision.proactive_enabled) await screenAPI.startProactive()
        else                                    await screenAPI.stopProactive()
        await save()
    }

    async function toggleVoice() {
        await settingsAPI.toggleVoice(cfg.value.voice.enabled)
        flash('✅ 已保存', true)
    }

    async function toggleQQ() {
        await settingsAPI.toggleQQ(cfg.value.qq.enabled)
        flash('✅ 已保存', true)
    }

    function applyOpacity()    { window.electronAPI?.setOpacity(cfg.value.window.opacity);         save() }
    function applyAlwaysOnTop(){ window.electronAPI?.setAlwaysOnTop(cfg.value.window.always_on_top); save() }
    function goBack()          { router.replace('/') }

    // 退出页面时兜底保存一次（防止快速关闭时 blur 未触发）
    onBeforeUnmount(async () => {
        if (isDirty.value && !blockSave.value) await settingsStore.update(cfg.value)
    })
</script>

<style scoped>
    /* ── 布局 ─────────────────────────────────────────────────────────────── */
    .settings-panel {
        display: flex;
        flex-direction: column;
        height: 100vh;
        background: rgb(18,18,22);
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

    .title { font-size: 14px; font-weight: 500; color: #c9b8f8; }

    .content {
        flex: 1;
        overflow-y: auto;
        padding: 12px 14px;
    }
    .content::-webkit-scrollbar { width: 4px; }
    .content::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

    .section      { margin-bottom: 20px; }
    .section-title {
        font-size: 11px; font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.08em;
        color: #555; margin-bottom: 10px;
    }
    .sub-title {
        font-size: 11px; font-weight: 500;
        color: #444; margin-bottom: 6px; padding-top: 2px;
    }

    /* ── 标题栏按钮 & Toast ─────────────────────────────────────────────── */
    .icon-btn {
        background: none; border: none; color: #888;
        font-size: 14px; padding: 3px 8px;
        border-radius: 6px; cursor: pointer;
    }
    .icon-btn:hover { background: rgba(255,255,255,0.08); color: #ddd; }

    .reload-btn { font-size: 16px; color: #7dd3fc; }
    .reload-btn:hover { color: #38bdf8; background: rgba(56,189,248,0.1); }

    /* 旋转动画 */
    .reload-btn.spinning {
        display: inline-block;
        animation: spin 0.7s linear infinite;
        color: #38bdf8;
    }
    @keyframes spin { to { transform: rotate(-360deg); } }

    /* 内联 Toast（标题栏右侧） */
    .reload-status {
        font-size: 11px; padding: 2px 8px;
        border-radius: 10px; white-space: nowrap;
    }
    .rstat-ok  { background: rgba(74,222,128,0.12); color: #4ade80; }
    .rstat-err { background: rgba(248,113,113,0.12); color: #f87171; }

    .toast-enter-active, .toast-leave-active { transition: opacity 0.3s; }
    .toast-enter-from, .toast-leave-to { opacity: 0; }

    /* ── 服务商网格 ───────────────────────────────────────────────────────── */
    .provider-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 5px;
        margin-top: 4px;
    }

    .provider-btn {
        position: relative;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        color: #999;
        font-size: 11px; padding: 5px 4px;
        border-radius: 6px; cursor: pointer;
        transition: all 0.15s;
        display: flex; align-items: center; justify-content: center; gap: 4px;
    }
    .provider-btn:hover { background: rgba(255,255,255,0.08); color: #ccc; }
    .provider-btn.active {
        background: rgba(139,92,246,0.2);
        border-color: rgba(139,92,246,0.5);
        color: #c9b8f8; font-weight: 500;
    }

    /* Key 状态小圆点（在服务商按钮右上角） */
    .key-dot {
        width: 6px; height: 6px;
        border-radius: 50%; flex-shrink: 0;
    }
    .dot-ok    { background: #4ade80; box-shadow: 0 0 4px rgba(74,222,128,0.5); }
    .dot-empty { background: rgba(255,255,255,0.15); }

    /* ── 字段 ──────────────────────────────────────────────────────────────── */
    .field {
        display: flex; flex-direction: column;
        gap: 4px; margin-bottom: 10px;
    }
    .field > span { font-size: 12px; color: #888; }

    .field input[type="text"],
    .field input[type="password"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px; color: #e8e8ec;
        font-size: 12px; padding: 6px 10px; outline: none;
    }
    .field input[type="text"]:focus,
    .field input[type="password"]:focus { border-color: rgba(139,92,246,0.4); }
    .field input.readonly { color: #555; cursor: default; }

    .field.toggle {
        flex-direction: row; align-items: center;
        justify-content: space-between;
    }

    /* Key 行（输入框 + 徽章） */
    .key-row {
        display: flex; align-items: center; gap: 6px;
    }
    .key-row input { flex: 1; }

    .key-badge {
        flex-shrink: 0; width: 18px; height: 18px;
        border-radius: 50%; font-size: 10px; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
    }
    .key-ok   { background: rgba(74,222,128,0.15); color: #4ade80; }
    .key-warn { background: rgba(245,158,11,0.15);  color: #f59e0b; }

    /* ── 模型预设按钮 ──────────────────────────────────────────────────────── */
    .model-presets {
        display: flex; gap: 5px; flex-wrap: wrap;
        margin-bottom: 5px;
    }

    .model-preset-btn {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        color: #777; font-size: 11px;
        padding: 4px 9px; border-radius: 5px;
        cursor: pointer; transition: all 0.15s;
        white-space: nowrap;
    }
    .model-preset-btn:hover { background: rgba(255,255,255,0.08); color: #bbb; }
    .model-custom-btn { border-style: dashed; color: #555; }
    .model-custom-btn:hover { color: #999; }
    .model-custom-btn.active { border-style: solid; }
    .model-preset-btn.active {
        background: rgba(139,92,246,0.18);
        border-color: rgba(139,92,246,0.4);
        color: #c9b8f8;
    }

    /* ── 参数滑块 ──────────────────────────────────────────────────────────── */
    .param-row    { margin-bottom: 14px; }
    .param-label  { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #888; margin-bottom: 5px; }
    .param-value  { background: rgba(139,92,246,0.15); color: #c9b8f8; font-size: 11px; padding: 1px 6px; border-radius: 4px; min-width: 32px; text-align: center; }
    .param-hint   { width: 15px; height: 15px; border-radius: 50%; background: rgba(255,255,255,0.08); color: #666; font-size: 10px; display: flex; align-items: center; justify-content: center; cursor: help; flex-shrink: 0; margin-left: auto; }
    .param-hint:hover { background: rgba(139,92,246,0.2); color: #c9b8f8; }
    .param-row input[type="range"] { width: 100%; accent-color: #8b5cf6; }
    .param-tips   { font-size: 10px; color: #444; margin-top: 3px; }

    /* ── 模块卡片 ──────────────────────────────────────────────────────────── */
    .module-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px; padding: 10px 12px;
        margin-bottom: 8px; transition: border-color 0.2s;
    }
    .module-card.active { border-color: rgba(139,92,246,0.3); }
    .module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
    .module-header > span { font-size: 13px; font-weight: 500; }
    .module-desc   { font-size: 11px; color: #555; }
    .module-status.warn { font-size: 11px; color: #facc15; margin-top: 4px; }

    /* ── 切换开关 ──────────────────────────────────────────────────────────── */
    .toggle-switch { position: relative; display: inline-block; width: 36px; height: 20px; }
    .toggle-switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; inset: 0; background: rgba(255,255,255,0.1); border-radius: 20px; transition: 0.2s; }
    .slider:before { content: ''; position: absolute; width: 14px; height: 14px; left: 3px; bottom: 3px; background: #888; border-radius: 50%; transition: 0.2s; }
    .toggle-switch input:checked + .slider { background: rgba(139,92,246,0.6); }
    .toggle-switch input:checked + .slider:before { transform: translateX(16px); background: #fff; }

    /* ── Vision 特有 ───────────────────────────────────────────────────────── */
    .vision-config { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }

    .route-indicator { display: flex; align-items: flex-start; gap: 8px; padding: 8px 10px; border-radius: 8px; margin-bottom: 10px; border: 1px solid transparent; }
    .route-ok   { background: rgba(74,222,128,0.06);  border-color: rgba(74,222,128,0.15); }
    .route-warn { background: rgba(245,158,11,0.06);  border-color: rgba(245,158,11,0.2); }
    .route-icon { font-size: 14px; flex-shrink: 0; margin-top: 1px; }
    .route-label { font-size: 12px; color: #c9d1d9; }
    .route-sub   { font-size: 11px; margin-top: 2px; }

    .info-box { font-size: 11px; line-height: 1.6; padding: 8px 10px; border-radius: 7px; margin-bottom: 8px; }
    .info-ok      { background: rgba(74,222,128,0.06);  color: #86efac; border: 1px solid rgba(74,222,128,0.15); }
    .info-neutral { background: rgba(255,255,255,0.03); color: #888;    border: 1px solid rgba(255,255,255,0.07); }

    .warn-box   { background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.2); border-radius: 8px; padding: 9px 11px; margin-bottom: 8px; }
    .warn-title { font-size: 11px; color: #f59e0b; margin-bottom: 5px; }
    .guide-toggle { font-size: 11px; color: #7dd3fc; cursor: pointer; user-select: none; }
    .guide-toggle:hover { color: #38bdf8; }
    .guide-body { margin-top: 8px; display: flex; flex-direction: column; gap: 7px; }
    .guide-step { display: flex; gap: 8px; align-items: flex-start; }
    .step-num   { background: rgba(56,189,248,0.2); color: #7dd3fc; font-size: 11px; font-weight: 600; width: 18px; height: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    .guide-step span   { font-size: 11px; color: #888; line-height: 1.6; }
    .guide-step strong { color: #c9d1d9; }
    .guide-step code   { background: rgba(255,255,255,0.06); padding: 1px 4px; border-radius: 3px; font-size: 10px; }
    .guide-note { font-size: 11px; color: #555; padding-top: 4px; border-top: 1px solid rgba(255,255,255,0.05); }

    .ok-box { font-size: 11px; color: #4ade80; padding: 5px 8px; background: rgba(74,222,128,0.06); border-radius: 6px; margin-bottom: 6px; }

    /* ── 其他 ──────────────────────────────────────────────────────────────── */
    .select-input {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px; color: #e8e8ec; font-size: 12px;
        padding: 6px 10px; outline: none; cursor: pointer;
    }
    .select-input:focus { border-color: rgba(139,92,246,0.4); }
    .select-input option { background: rgb(28,28,35); }

    .hint-inline { font-size: 10px; color: #444; font-weight: normal; }
    .hint-inline.required { color: #f59e0b; }

    .btn-secondary {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
        color: #c9b8f8; font-size: 12px; padding: 7px 12px;
        border-radius: 8px; cursor: pointer; width: 100%; text-align: left;
    }
    .btn-secondary:hover { background: rgba(255,255,255,0.09); }
</style>