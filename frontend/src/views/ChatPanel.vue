<template>
    <div class="chat-panel">
        <!-- 标题栏（可拖动） -->
        <div class="titlebar" style="-webkit-app-region: drag">
            <span class="pet-name">{{ petName }}</span>
            <div class="titlebar-actions" style="-webkit-app-region: no-drag">
                <button class="clear-btn" title="清空对话" @click="clearChat">🗑 清空</button>
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
                 :class="msg.role">
                <div class="bubble">
                    <span v-if="msg.role === 'assistant' && msg.streaming" class="typing-cursor">{{ msg.content }}<span class="cursor">▊</span></span>
                    <span v-else>{{ msg.content }}</span>
                </div>
            </div>
            <div v-if="chatStore.messages.length === 0" class="empty-hint">
                {{ greeting }}
            </div>
        </div>

        <!-- 输入区 -->
        <div class="input-area">
            <textarea ref="inputEl"
                      v-model="inputText"
                      placeholder="说点什么... (Enter 发送)"
                      @keydown.enter.exact.prevent="sendMessage"
                      @keydown.enter.shift.exact="inputText += '\n'"
                      :disabled="chatStore.isStreaming"
                      rows="1" />
            <button class="send-btn" :disabled="chatStore.isStreaming || !inputText.trim()" @click="sendMessage">
                {{ chatStore.isStreaming ? '…' : '↑' }}
            </button>
        </div>
    </div>
</template>

<script setup>
    import { ref, computed, watch, nextTick, onMounted } from 'vue'
    import { useChatStore } from '@/stores/chat'
    import { useSettingsStore } from '@/stores/settings'

    const chatStore = useChatStore()
    const settingsStore = useSettingsStore()

    const inputText = ref('')
    const messagesEl = ref(null)
    const inputEl = ref(null)
    const backendOk = ref(false)

    const petName = computed(() =>
        settingsStore.config?.ai?.text_model ? 'AiPet' : 'AiPet'
    )
    const greeting = ref('你好！有什么可以帮你的吗？(ﾟ▽ﾟ)/')
    const statusText = computed(() => {
        if (!backendOk.value) return '后端未连接'
        if (chatStore.isStreaming) return '正在思考...'
        return '在线'
    })
    const statusClass = computed(() => ({
        'status-ok': backendOk.value && !chatStore.isStreaming,
        'status-thinking': chatStore.isStreaming,
        'status-error': !backendOk.value,
    }))

    async function checkBackend() {
        try {
            const res = await fetch('http://localhost:8000/health')
            backendOk.value = res.ok
        } catch {
            backendOk.value = false
        }
    }

    async function sendMessage() {
        const text = inputText.value.trim()
        if (!text || chatStore.isStreaming) return
        inputText.value = ''
        await chatStore.sendMessage(text)
    }

    async function clearChat() {
        if (confirm('清空对话历史？')) await chatStore.clearHistory()
    }

    function hideWindow() {
        window.electronAPI?.toggleWindow()
    }

    // 自动滚动到底部
    watch(() => chatStore.messages, async () => {
        await nextTick()
        if (messagesEl.value) {
            messagesEl.value.scrollTop = messagesEl.value.scrollHeight
        }
    }, { deep: true })

    onMounted(async () => {
        await checkBackend()
        await chatStore.loadHistory()
        setInterval(checkBackend, 5000)
    })
</script>

<style scoped>
    .chat-panel {
        display: flex;
        flex-direction: column;
        height: 100vh;
        background: rgb(18, 18, 22); /* 纯不透明，透明度由 Electron 窗口控制 */
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

        .icon-btn:hover {
            background: rgba(255,255,255,0.08);
            color: #ddd;
        }

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

        .clear-btn:hover {
            background: rgba(239,68,68,0.18);
            border-color: rgba(239,68,68,0.4);
        }

    .status-bar {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        font-size: 11px;
        color: #888;
    }

    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #555;
    }

    .status-ok .status-dot {
        background: #4ade80;
    }

    .status-thinking .status-dot {
        background: #facc15;
        animation: pulse 1s infinite;
    }

    .status-error .status-dot {
        background: #f87171;
    }

    @keyframes pulse {
        0%,100% {
            opacity: 1
        }

        50% {
            opacity: 0.4
        }
    }

    .messages {
        flex: 1;
        overflow-y: auto;
        padding: 12px 12px 4px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

        .messages::-webkit-scrollbar {
            width: 4px;
        }

        .messages::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
        }

    .message {
        display: flex;
    }

        .message.user {
            justify-content: flex-end;
        }

        .message.assistant {
            justify-content: flex-start;
        }

    .bubble {
        max-width: 82%;
        padding: 8px 12px;
        border-radius: 12px;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .user .bubble {
        background: rgba(139, 92, 246, 0.3);
        border: 1px solid rgba(139,92,246,0.2);
    }

    .assistant .bubble {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.06);
    }

    .cursor {
        animation: blink 0.8s step-end infinite;
    }

    @keyframes blink {
        0%,100% {
            opacity: 1
        }

        50% {
            opacity: 0
        }
    }

    .empty-hint {
        text-align: center;
        color: #555;
        font-size: 13px;
        margin-top: 60px;
    }

    .input-area {
        display: flex;
        align-items: flex-end;
        gap: 8px;
        padding: 10px 12px;
        border-top: 1px solid rgba(255,255,255,0.06);
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

        textarea:focus {
            border-color: rgba(139,92,246,0.4);
        }

        textarea:disabled {
            opacity: 0.5;
        }

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

        .send-btn:hover:not(:disabled) {
            background: rgba(139,92,246,0.9);
        }

        .send-btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }
</style>