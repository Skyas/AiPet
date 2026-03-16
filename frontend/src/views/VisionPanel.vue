<template>
    <div class="vision-panel">
        <!-- 标题栏 -->
        <div class="titlebar" style="-webkit-app-region: drag">
            <div class="title-left">
                <span class="dot" :class="statusDotClass"></span>
                <span class="title">游戏陪玩</span>
            </div>
            <button class="icon-btn" style="-webkit-app-region: no-drag" @click="goBack">✕</button>
        </div>

        <!-- 主体：观察流 -->
        <div class="feed" ref="feedEl">
            <!-- 空态 -->
            <div class="empty" v-if="!observations.length && !isAnalyzing">
                <div class="empty-icon">🎮</div>
                <div class="empty-title">让 AI 陪你一起玩</div>
                <div class="empty-hint">
                    开启主动模式后，AI 会定时观察你的屏幕，<br />
                    在合适的时机主动跟你搭话。<br />
                    或者点「分析当前画面」手动触发一次。
                </div>
            </div>

            <!-- 观察条目列表（最新的在最下面，像聊天记录） -->
            <div v-for="(item, idx) in observations"
                 :key="idx"
                 class="obs-item"
                 :class="{ 'has-reply': item.commentary }">
                <!-- 时间戳 + 触发来源 -->
                <div class="obs-meta">
                    <span class="obs-time">{{ item.timeLabel }}</span>
                    <span class="obs-source" :class="item.source">
                        {{ sourceLabel(item.source) }}
                    </span>
                </div>

                <!-- 视觉描述（可折叠，默认收起） -->
                <div class="vision-row" @click="item.showDesc = !item.showDesc">
                    <span class="vision-icon">👁</span>
                    <span class="vision-summary">{{ truncate(item.visionDesc, 40) }}</span>
                    <span class="toggle-chevron">{{ item.showDesc ? '▲' : '▼' }}</span>
                </div>
                <div class="vision-full" v-if="item.showDesc">{{ item.visionDesc }}</div>

                <!-- AI 点评 -->
                <div class="commentary" v-if="item.commentary || (idx === observations.length - 1 && isAnalyzing)">
                    <span class="commentary-icon">💬</span>
                    <span class="commentary-text">
                        {{ item.commentary }}
                        <span class="cursor" v-if="idx === observations.length - 1 && isStreaming">▋</span>
                    </span>
                </div>
            </div>

            <!-- 正在分析的实时进度条（放在列表末尾，像"正在输入"） -->
            <div class="analyzing-row" v-if="isAnalyzing && !isStreaming">
                <span class="spinner">⟳</span>
                <span>{{ progressLabel }}</span>
            </div>
        </div>

        <!-- 底部操作栏 -->
        <div class="bottom-bar">
            <!-- 主动模式开关 -->
            <div class="proactive-toggle"
                 :class="{ active: proactiveRunning }"
                 @click="toggleProactive"
                 :title="proactiveRunning ? '点击停止主动互动' : '点击开启主动互动'">
                <span>{{ proactiveRunning ? '⏹' : '▶' }}</span>
                <span class="toggle-label">
                    {{ proactiveRunning ? `主动中 · ${checkInterval}s` : '主动模式' }}
                </span>
            </div>

            <!-- 手动分析 -->
            <button class="analyze-btn"
                    :disabled="isAnalyzing"
                    @click="manualAnalyze">
                {{ isAnalyzing ? '分析中…' : '分析当前画面' }}
            </button>

            <!-- 设置入口 -->
            <button class="settings-btn" @click="$router.replace('/settings')" title="Vision 设置">⚙</button>
        </div>
    </div>
</template>

<script setup>
    import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
    import { useRouter } from 'vue-router'
    import { useSettingsStore } from '@/stores/settings'
    import { screenAPI } from '@/utils/api'
    import { useSocket } from '@/utils/socket'

    const router = useRouter()
    const settingsStore = useSettingsStore()
    const { socket } = useSocket()
    const feedEl = ref(null)

    // ── 状态 ──────────────────────────────────────────────────────────────────────
    const observations = ref([])   // 观察条目列表，每条包含 visionDesc + commentary
    const isAnalyzing = ref(false) // 是否正在分析中（截图 or 视觉分析阶段）
    const isStreaming = ref(false) // 是否正在流式生成 AI 点评
    const progressKey = ref('')    // 当前阶段 key（'capturing' / 'analyzing_vision' / 'generating'）
    const proactiveRunning = ref(false)

    // ── 计算属性 ──────────────────────────────────────────────────────────────────
    const checkInterval = computed(() => settingsStore.config?.vision?.proactive_check_interval ?? 45)

    const statusDotClass = computed(() => {
        if (isAnalyzing.value) return 'dot-active pulse'
        if (proactiveRunning.value) return 'dot-proactive'
        return 'dot-idle'
    })

    const progressLabel = computed(() => {
        const map = { capturing: '截图中…', analyzing_vision: '识别画面…', generating: 'AI 思考中…' }
        return map[progressKey.value] ?? '处理中…'
    })

    function sourceLabel(src) {
        const map = { manual: '手动', proactive: 'AI 主动', user_chat: '对话触发' }
        return map[src] ?? src
    }

    function truncate(str, n) {
        return str && str.length > n ? str.slice(0, n) + '…' : str
    }

    // ── 手动分析 ──────────────────────────────────────────────────────────────────
    async function manualAnalyze() {
        if (isAnalyzing.value) return

        // 创建一个新的观察条目占位
        const item = reactive({
            visionDesc: '',
            commentary: '',
            source: 'manual',
            timeLabel: formatNow(),
            showDesc: false,
        })
        observations.value.push(item)
        isAnalyzing.value = true
        isStreaming.value = false
        scrollFeed()

        await screenAPI.analyze({
            onStatus(k) {
                progressKey.value = k
                if (k === 'generating') {
                    isAnalyzing.value = false
                    isStreaming.value = true
                }
            },
            onVisionDesc(d) {
                item.visionDesc = d
                scrollFeed()
            },
            onToken(t) {
                item.commentary += t
                scrollFeed()
            },
            onDone() {
                isStreaming.value = false
                progressKey.value = ''
            },
            onError(e) {
                item.commentary = `[错误] ${e}`
                isAnalyzing.value = false
                isStreaming.value = false
                progressKey.value = ''
            },
        })
    }

    // ── 主动模式开关 ──────────────────────────────────────────────────────────────
    async function toggleProactive() {
        if (proactiveRunning.value) {
            await screenAPI.stopProactive()
            proactiveRunning.value = false
        } else {
            await screenAPI.startProactive()
            proactiveRunning.value = true
        }
    }

    // ── 接收 Socket.IO 主动消息推送 ───────────────────────────────────────────────
    // 主动引擎在后台触发时，通过 Socket.IO 推送 proactive_message 事件
    // VisionPanel 接收后新增一条观察记录；ChatPanel 同样应监听此事件展示在对话流里
    function handleProactiveMessage(data) {
        const item = {
            visionDesc: data.vision_desc || '',
            commentary: data.content || '',
            source: 'proactive',
            timeLabel: formatNow(),
            showDesc: false,
        }
        observations.value.push(item)
        scrollFeed()
    }

    // ── 滚动 ──────────────────────────────────────────────────────────────────────
    function scrollFeed() {
        nextTick(() => {
            if (feedEl.value) {
                feedEl.value.scrollTop = feedEl.value.scrollHeight
            }
        })
    }

    function formatNow() {
        const now = new Date()
        return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
    }

    function goBack() { router.replace('/') }

    // ── 生命周期 ──────────────────────────────────────────────────────────────────
    onMounted(async () => {
        await settingsStore.load()

        // 查询后端当前状态（后端可能已经在运行主动引擎）
        try {
            const status = await screenAPI.getStatus()
            proactiveRunning.value = status.proactive_running

            // 如果后端有最近一次的观察记录，展示出来
            if (status.last_vision_desc) {
                observations.value.push({
                    visionDesc: status.last_vision_desc,
                    commentary: status.last_reply || '',
                    source: 'proactive',
                    timeLabel: status.last_timestamp
                        ? new Date(status.last_timestamp * 1000).toLocaleTimeString()
                        : '—',
                    showDesc: false,
                })
            }
        } catch { }

        // 监听主动消息推送
        socket?.on('proactive_message', handleProactiveMessage)
    })

    onUnmounted(() => {
        socket?.off('proactive_message', handleProactiveMessage)
    })

    // reactive 需要从 vue 引入（script setup 里没有自动导入的话补上）
    import { reactive } from 'vue'
</script>

<style scoped>
    .vision-panel {
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

    /* ── 标题栏 ── */
    .titlebar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        flex-shrink: 0;
    }

    .title-left {
        display: flex;
        align-items: center;
        gap: 7px;
    }

    .title {
        font-size: 14px;
        font-weight: 500;
        color: #a5f3fc;
    }

    .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        transition: background 0.3s;
    }

    .dot-idle {
        background: #444;
    }

    .dot-proactive {
        background: #38bdf8;
    }

    .dot-active {
        background: #f59e0b;
    }

    .pulse {
        animation: pulse 1.2s infinite;
    }

    @keyframes pulse {
        0%,100% {
            opacity: 1
        }

        50% {
            opacity: 0.25
        }
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

    /* ── 观察流 ── */
    .feed {
        flex: 1;
        overflow-y: auto;
        padding: 10px 12px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

        .feed::-webkit-scrollbar {
            width: 3px;
        }

        .feed::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.08);
            border-radius: 2px;
        }

    /* 空态 */
    .empty {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        text-align: center;
        padding: 20px 10px;
    }

    .empty-icon {
        font-size: 36px;
        opacity: 0.25;
    }

    .empty-title {
        font-size: 14px;
        color: #666;
        font-weight: 500;
    }

    .empty-hint {
        font-size: 11px;
        color: #3a3a3a;
        line-height: 1.7;
    }

    /* 观察条目 */
    .obs-item {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 9px 11px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        transition: border-color 0.2s;
    }

        .obs-item.has-reply {
            border-color: rgba(165,243,252,0.1);
        }

    .obs-meta {
        display: flex;
        align-items: center;
        gap: 7px;
    }

    .obs-time {
        font-size: 10px;
        color: #444;
    }

    .obs-source {
        font-size: 10px;
        padding: 1px 6px;
        border-radius: 4px;
    }

        .obs-source.manual {
            background: rgba(139,92,246,0.15);
            color: #c9b8f8;
        }

        .obs-source.proactive {
            background: rgba(56,189,248,0.12);
            color: #7dd3fc;
        }

        .obs-source.user_chat {
            background: rgba(74,222,128,0.12);
            color: #86efac;
        }

    /* 视觉描述行（可折叠） */
    .vision-row {
        display: flex;
        align-items: center;
        gap: 5px;
        cursor: pointer;
        user-select: none;
    }

        .vision-row:hover {
            opacity: 0.85;
        }

    .vision-icon {
        font-size: 11px;
        flex-shrink: 0;
    }

    .vision-summary {
        font-size: 11px;
        color: #666;
        flex: 1;
    }

    .toggle-chevron {
        font-size: 9px;
        color: #444;
        flex-shrink: 0;
    }

    .vision-full {
        font-size: 11px;
        color: #555;
        line-height: 1.6;
        padding: 4px 0 2px 18px;
        border-left: 2px solid rgba(255,255,255,0.06);
        margin-left: 2px;
    }

    /* AI 点评 */
    .commentary {
        display: flex;
        gap: 6px;
        align-items: flex-start;
    }

    .commentary-icon {
        font-size: 12px;
        flex-shrink: 0;
        margin-top: 1px;
    }

    .commentary-text {
        font-size: 12px;
        color: #c9d1d9;
        line-height: 1.65;
    }

    .cursor {
        animation: blink 1s infinite;
    }

    @keyframes blink {
        0%,100% {
            opacity: 1
        }

        50% {
            opacity: 0
        }
    }

    /* 正在分析提示 */
    .analyzing-row {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        color: #555;
        padding: 4px 4px;
    }

    .spinner {
        display: inline-block;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    /* ── 底部操作栏 ── */
    .bottom-bar {
        padding: 8px 12px;
        border-top: 1px solid rgba(255,255,255,0.06);
        display: flex;
        align-items: center;
        gap: 7px;
        flex-shrink: 0;
    }

    .proactive-toggle {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 6px 10px;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
        cursor: pointer;
        transition: all 0.15s;
        flex-shrink: 0;
        font-size: 11px;
    }

        .proactive-toggle:hover {
            background: rgba(255,255,255,0.07);
        }

        .proactive-toggle.active {
            border-color: rgba(56,189,248,0.35);
            background: rgba(56,189,248,0.08);
        }

    .toggle-label {
        white-space: nowrap;
        color: #888;
    }

    .proactive-toggle.active .toggle-label {
        color: #7dd3fc;
    }

    .analyze-btn {
        flex: 1;
        background: rgba(139,92,246,0.18);
        border: 1px solid rgba(139,92,246,0.35);
        color: #c9b8f8;
        font-size: 12px;
        font-weight: 500;
        padding: 7px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.15s;
    }

        .analyze-btn:hover:not(:disabled) {
            background: rgba(139,92,246,0.3);
        }

        .analyze-btn:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }

    .settings-btn {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        color: #666;
        font-size: 13px;
        width: 30px;
        height: 30px;
        border-radius: 7px;
        cursor: pointer;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }

        .settings-btn:hover {
            background: rgba(255,255,255,0.08);
            color: #aaa;
        }
</style>