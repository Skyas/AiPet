<template>
    <div class="chat-panel">
        <!-- 标题栏 -->
        <div class="titlebar" style="-webkit-app-region: drag">
            <span class="pet-name">{{ petName }}</span>
            <div class="titlebar-actions" style="-webkit-app-region: no-drag">
                <button class="clear-btn" title="清空对话" @click="clearChat">🗑 清空</button>
                <button class="icon-btn" title="观察记录" @click="$router.replace('/vision')">👁</button>
                <button class="icon-btn" title="设置" @click="$router.replace('/settings')">⚙</button>
                <button class="icon-btn" title="收起" @click="hideWindow">─</button>
            </div>
        </div>

        <!-- 状态栏 -->
        <div class="status-bar" :class="statusClass">
            <span class="status-dot"></span>
            <span>{{ statusText }}</span>
        </div>

        <!-- 消息列表 -->
        <div class="messages" ref="messagesEl">
            <div v-for="msg in chatStore.messages"
                 :key="msg.id"
                 class="message"
                 :class="[msg.role, { proactive: msg.proactive }]">
                <div class="bubble">
                    <span class="proactive-badge" v-if="msg.proactive">AI 主动</span>
                    <span v-if="msg.role === 'assistant' && msg.streaming" class="typing-cursor">
                        {{ msg.content }}<span class="cursor">▊</span>
                    </span>
                    <span v-else>{{ msg.content }}</span>
                </div>
            </div>
            <div v-if="chatStore.messages.length === 0" class="empty-hint">
                {{ greeting }}
            </div>
        </div>

        <!-- 输入框（仅 showInput 时展开） -->
        <transition name="slide-up">
            <div class="input-area" v-if="showInput">
                <textarea ref="inputEl"
                          v-model="inputText"
                          placeholder="说点什么... (Enter 发送)"
                          @keydown.enter.exact.prevent="sendMessage"
                          @keydown.enter.shift.exact="inputText += '\n'"
                          :disabled="chatStore.isStreaming"
                          rows="1" />
                <button class="send-btn"
                        :disabled="chatStore.isStreaming || !inputText.trim()"
                        @click="sendMessage">
                    {{ chatStore.isStreaming ? '…' : '↑' }}
                </button>
            </div>
        </transition>

        <!-- 底部工具栏 -->
        <div class="bottom-bar">

            <!-- 文字输入 -->
            <button class="tool-btn"
                    :class="{ active: showInput }"
                    @click="toggleInput"
                    title="文字输入">
                <span class="tool-icon">✏️</span>
                <span class="tool-label">输入</span>
            </button>

            <!-- 截图分析 -->
            <button class="tool-btn"
                    :class="{ loading: isAnalyzing }"
                    :disabled="isAnalyzing"
                    @click="manualAnalyze"
                    title="分析当前画面">
                <span class="tool-icon">{{ isAnalyzing ? '⟳' : '📷' }}</span>
                <span class="tool-label">{{ isAnalyzing ? '分析中' : '截图' }}</span>
            </button>

            <!-- 陪玩模式 -->
            <button class="tool-btn tool-btn--proactive"
                    :class="{ active: proactiveRunning }"
                    @click="toggleProactive"
                    title="陪玩模式">
                <span class="tool-icon">🎮</span>
                <span class="tool-label">陪玩</span>
            </button>

            <!-- 语音（占位，Phase 3） -->
            <button class="tool-btn tool-btn--disabled" disabled title="语音功能即将开放">
                <span class="tool-icon">🎙</span>
                <span class="tool-label">语音</span>
            </button>

            <!-- QQ 监控（占位，Phase 4） -->
            <button class="tool-btn tool-btn--disabled" disabled title="QQ 功能即将开放">
                <span class="tool-icon">🐧</span>
                <span class="tool-label">QQ</span>
            </button>

        </div>
    </div>
</template>

<script setup>
    import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
    import { useChatStore } from '@/stores/chat'
    import { useSettingsStore } from '@/stores/settings'
    import { screenAPI } from '@/utils/api'
    import { useSocket } from '@/utils/socket'

    const chatStore = useChatStore()
    const settingsStore = useSettingsStore()
    const { socket } = useSocket()

    const inputText    = ref('')
    const messagesEl   = ref(null)
    const inputEl      = ref(null)
    const backendOk    = ref(false)
    const showInput    = ref(false)
    const isAnalyzing  = ref(false)
    const proactiveRunning = ref(false)

    const petName = computed(() => 'AiPet')
    const greeting = ref('你好！有什么可以帮你的吗？(ﾟ▽ﾟ)/')

    const statusText = computed(() => {
        if (!backendOk.value)      return '后端未连接'
        if (isAnalyzing.value)     return '画面分析中...'
        if (chatStore.isStreaming)  return '正在思考...'
        if (proactiveRunning.value) return '陪玩模式运行中'
        return '在线'
    })
    const statusClass = computed(() => ({
        'status-ok':       backendOk.value && !chatStore.isStreaming && !isAnalyzing.value,
        'status-thinking': chatStore.isStreaming || isAnalyzing.value,
        'status-proactive': proactiveRunning.value && !chatStore.isStreaming && !isAnalyzing.value,
        'status-error':    !backendOk.value,
    }))

    // ── 输入框开关 ──────────────────────────────────────────────────────────
    function toggleInput() {
        showInput.value = !showInput.value
        if (showInput.value) {
            nextTick(() => inputEl.value?.focus())
        }
    }

    // ── 发送消息 ────────────────────────────────────────────────────────────
    async function sendMessage() {
        const text = inputText.value.trim()
        if (!text || chatStore.isStreaming) return
        inputText.value = ''
        await chatStore.sendMessage(text)
        scrollMessages()
    }

    // ── 截图分析 ────────────────────────────────────────────────────────────
    async function manualAnalyze() {
        if (isAnalyzing.value) return
        isAnalyzing.value = true
        // 在聊天流里插入一条系统提示
        chatStore.messages.push({
            id: Date.now(),
            role: 'assistant',
            content: '👁 正在分析当前画面...',
            proactive: false,
            streaming: false,
        })
        scrollMessages()

        await screenAPI.analyze({
            onToken(t) {
                // 把流式 token 追加到最后一条消息
                const last = chatStore.messages[chatStore.messages.length - 1]
                if (last && last.role === 'assistant') {
                    if (last.content === '👁 正在分析当前画面...') last.content = ''
                    last.content += t
                    last.streaming = true
                    scrollMessages()
                }
            },
            onDone() {
                const last = chatStore.messages[chatStore.messages.length - 1]
                if (last) last.streaming = false
                isAnalyzing.value = false
            },
            onError(e) {
                const last = chatStore.messages[chatStore.messages.length - 1]
                if (last) { last.content = `[截图分析失败] ${e}`; last.streaming = false }
                isAnalyzing.value = false
            },
        })
    }

    // ── 陪玩模式 ────────────────────────────────────────────────────────────
    async function toggleProactive() {
        if (proactiveRunning.value) {
            await screenAPI.stopProactive()
            proactiveRunning.value = false
        } else {
            await screenAPI.startProactive()
            proactiveRunning.value = true
        }
    }

    // ── 其他 ────────────────────────────────────────────────────────────────
    async function clearChat() {
        if (confirm('清空对话历史？')) await chatStore.clearHistory()
    }

    function hideWindow() {
        window.electronAPI?.toggleWindow()
    }

    function scrollMessages() {
        nextTick(() => {
            if (messagesEl.value)
                messagesEl.value.scrollTop = messagesEl.value.scrollHeight
        })
    }

    async function checkBackend() {
        try {
            const res = await fetch('http://localhost:8001/health')
            backendOk.value = res.ok
        } catch {
            backendOk.value = false
        }
    }

    // 自动滚动
    watch(() => chatStore.messages, scrollMessages, { deep: true })

    // 主动消息推送
    function handleProactiveMessage(data) {
        chatStore.messages.push({
            id: Date.now(),
            role: 'assistant',
            content: data.content,
            proactive: true,
            streaming: false,
        })
        scrollMessages()
    }

    onMounted(async () => {
        await checkBackend()
        await chatStore.loadHistory()
        setInterval(checkBackend, 5000)

        // 同步陪玩引擎状态
        try {
            const status = await screenAPI.getStatus()
            proactiveRunning.value = status.proactive_running ?? false
        } catch { }

        socket.on('proactive_message', handleProactiveMessage)
    })

    onUnmounted(() => {
        socket.off('proactive_message', handleProactiveMessage)
    })
</script>

<style scoped>
    .chat-panel {
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

    /* ── 标题栏 ──────────────────────────────────────────────────────────── */
    .titlebar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        flex-shrink: 0;
    }

    .pet-name {
        font-size: 14px;
        font-weight: 500;
        color: #c9b8f8;
    }

    .titlebar-actions {
        display: flex;
        gap: 4px;
        align-items: center;
    }

    .icon-btn {
        background: none;
        border: none;
        color: #888;
        font-size: 13px;
        padding: 3px 6px;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.15s;
    }
    .icon-btn:hover { background: rgba(255,255,255,0.08); color: #ddd; }

    .clear-btn {
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.2);
        color: #f87171;
        font-size: 11px;
        padding: 3px 8px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s;
        display: flex;
        align-items: center;
        gap: 3px;
    }
    .clear-btn:hover { background: rgba(239,68,68,0.18); border-color: rgba(239,68,68,0.4); }

    /* ── 状态栏 ──────────────────────────────────────────────────────────── */
    .status-bar {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        font-size: 11px;
        color: #888;
        flex-shrink: 0;
    }

    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #555;
        transition: background 0.3s;
    }

    .status-ok .status-dot       { background: #4ade80; }
    .status-thinking .status-dot { background: #facc15; animation: pulse 1s infinite; }
    .status-proactive .status-dot{ background: #38bdf8; animation: pulse 1.5s infinite; }
    .status-error .status-dot    { background: #f87171; }

    @keyframes pulse {
        0%,100% { opacity: 1 }
        50%      { opacity: 0.35 }
    }

    /* ── 消息列表 ────────────────────────────────────────────────────────── */
    .messages {
        flex: 1;
        overflow-y: auto;
        padding: 12px 12px 4px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .messages::-webkit-scrollbar { width: 4px; }
    .messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

    .message { display: flex; }
    .message.user      { justify-content: flex-end; }
    .message.assistant { justify-content: flex-start; }

    .bubble {
        max-width: 82%;
        padding: 8px 12px;
        border-radius: 12px;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-word;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .user .bubble {
        background: rgba(139,92,246,0.3);
        border: 1px solid rgba(139,92,246,0.2);
    }
    .assistant .bubble {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.06);
    }
    .message.proactive .bubble {
        border-color: rgba(56,189,248,0.25);
        background: rgba(56,189,248,0.05);
    }

    .proactive-badge {
        font-size: 10px;
        color: #38bdf8;
        opacity: 0.7;
        align-self: flex-start;
    }

    .cursor { animation: blink 0.8s step-end infinite; }
    @keyframes blink { 0%,100% { opacity: 1 } 50% { opacity: 0 } }

    .empty-hint {
        text-align: center;
        color: #555;
        font-size: 13px;
        margin-top: 60px;
    }

    /* ── 输入区（可展开）────────────────────────────────────────────────── */
    .input-area {
        display: flex;
        align-items: flex-end;
        gap: 8px;
        padding: 8px 12px;
        border-top: 1px solid rgba(255,255,255,0.06);
        flex-shrink: 0;
    }

    textarea {
        flex: 1;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        color: #e8e8ec;
        font-size: 13px;
        padding: 8px 10px;
        resize: none;
        outline: none;
        max-height: 100px;
        overflow-y: auto;
        font-family: inherit;
        line-height: 1.5;
    }
    textarea:focus   { border-color: rgba(139,92,246,0.4); }
    textarea:disabled{ opacity: 0.5; }

    .send-btn {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        border: none;
        background: rgba(139,92,246,0.6);
        color: white;
        font-size: 15px;
        cursor: pointer;
        transition: background 0.15s;
        flex-shrink: 0;
    }
    .send-btn:hover:not(:disabled) { background: rgba(139,92,246,0.9); }
    .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

    /* 滑入动画 */
    .slide-up-enter-active, .slide-up-leave-active {
        transition: all 0.2s ease;
    }
    .slide-up-enter-from, .slide-up-leave-to {
        opacity: 0;
        transform: translateY(6px);
    }

    /* ── 底部工具栏 ──────────────────────────────────────────────────────── */
    .bottom-bar {
        display: flex;
        align-items: center;
        justify-content: space-around;
        padding: 6px 8px 8px;
        border-top: 1px solid rgba(255,255,255,0.06);
        flex-shrink: 0;
    }

    .tool-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 3px;
        width: 50px;
        height: 50px;
        border-radius: 12px;
        border: 1px solid transparent;
        background: transparent;
        cursor: pointer;
        transition: all 0.15s;
        color: #666;
    }
    .tool-btn:hover:not(:disabled) {
        background: rgba(255,255,255,0.06);
        border-color: rgba(255,255,255,0.08);
        color: #aaa;
    }

    /* 激活态：文字输入 */
    .tool-btn.active {
        background: rgba(139,92,246,0.15);
        border-color: rgba(139,92,246,0.35);
        color: #c9b8f8;
    }

    /* 激活态：陪玩模式（青蓝发光） */
    .tool-btn--proactive.active {
        background: rgba(56,189,248,0.12);
        border-color: rgba(56,189,248,0.35);
        color: #7dd3fc;
        box-shadow: 0 0 10px rgba(56,189,248,0.15);
    }

    /* 加载态：截图分析中 */
    .tool-btn.loading {
        background: rgba(250,204,21,0.08);
        border-color: rgba(250,204,21,0.2);
        color: #fcd34d;
    }
    .tool-btn.loading .tool-icon {
        display: inline-block;
        animation: spin 1s linear infinite;
    }

    /* 禁用占位态 */
    .tool-btn--disabled {
        opacity: 0.22;
        cursor: not-allowed;
    }

    .tool-icon {
        font-size: 18px;
        line-height: 1;
    }

    .tool-label {
        font-size: 10px;
        line-height: 1;
        letter-spacing: 0.02em;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
</style>