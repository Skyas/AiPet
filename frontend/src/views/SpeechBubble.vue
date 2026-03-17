<template>
    <transition name="bubble-fade">
        <div class="bubble-root" v-if="visible">
            <!-- 尾巴指向上方（气泡在球下方）-->
            <div class="tail tail-top" v-if="!tailAtBottom" :style="{ left: tailX + 'px' }"></div>

            <!-- 主气泡 -->
            <div class="bubble-box">
                <span class="bubble-text">{{ text }}</span>
                <!-- 倒计时进度条 -->
                <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
                </div>
            </div>

            <!-- 尾巴指向下方（气泡在球上方，默认）-->
            <div class="tail tail-bottom" v-if="tailAtBottom" :style="{ left: tailX + 'px' }"></div>
        </div>
    </transition>
</template>

<script setup>
    import { ref, onMounted, onUnmounted } from 'vue'

    const visible     = ref(false)
    const text        = ref('')
    const tailAtBottom = ref(true)
    const tailX        = ref(100)   // px from left edge of bubble
    const progressPct  = ref(100)

    let dismissTimer   = null
    let progressTimer  = null
    const TICK_MS = 50

    function showBubble({ text: t }) {
        // 重置旧计时器
        clearTimeout(dismissTimer)
        clearInterval(progressTimer)

        text.value    = t
        visible.value = true
        progressPct.value = 100

        // 时长：3s 基础 + 每 8 字 1s，最长 20s
        const duration = Math.min(3000 + Math.ceil(t.length / 8) * 1000, 20000)
        const startTime = Date.now()

        progressTimer = setInterval(() => {
            const elapsed = Date.now() - startTime
            progressPct.value = Math.max(0, 100 - (elapsed / duration) * 100)
        }, TICK_MS)

        dismissTimer = setTimeout(() => {
            visible.value = false
            clearInterval(progressTimer)
        }, duration)
    }

    function updateTail({ tailAtBottom: atBottom, tailX: tx }) {
        tailAtBottom.value = atBottom
        // 限制尾巴在气泡宽度范围内（留 20px margin）
        tailX.value = Math.max(20, Math.min(tx - 8, 232))
    }

    onMounted(() => {
        window.electronAPI?.onBubbleContent(showBubble)
        window.electronAPI?.onBubbleTail(updateTail)
    })

    onUnmounted(() => {
        clearTimeout(dismissTimer)
        clearInterval(progressTimer)
    })
</script>

<style scoped>
    .bubble-root {
        width: 260px;
        display: flex;
        flex-direction: column;
        align-items: stretch;
        pointer-events: none;
        padding: 0 4px;
    }

    /* ── 气泡主体 ─────────────────────────────────────────────────────────── */
    .bubble-box {
        background: rgba(13, 11, 26, 0.88);
        border: 1px solid rgba(139,92,246,0.28);
        border-radius: 14px;
        padding: 9px 13px 7px;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .bubble-text {
        font-size: 12px;
        line-height: 1.65;
        color: #d4d0e8;
        font-family: system-ui, sans-serif;
        word-break: break-word;
        white-space: pre-wrap;
    }

    /* ── 进度条 ──────────────────────────────────────────────────────────── */
    .progress-bar {
        height: 2px;
        background: rgba(255,255,255,0.07);
        border-radius: 1px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: rgba(139,92,246,0.5);
        border-radius: 1px;
        transition: width 0.05s linear;
    }

    /* ── 尾巴（CSS 三角形）──────────────────────────────────────────────── */
    .tail {
        position: relative;
        width: 0;
        height: 0;
    }

    /* 尾巴朝下（气泡在球上方，默认） */
    .tail-bottom {
        margin-top: -1px;
        border-left:  9px solid transparent;
        border-right: 9px solid transparent;
        border-top:   10px solid rgba(13, 11, 26, 0.88);
    }

    /* 尾巴朝上（气泡在球下方） */
    .tail-top {
        margin-bottom: -1px;
        border-left:  9px solid transparent;
        border-right: 9px solid transparent;
        border-bottom: 10px solid rgba(13, 11, 26, 0.88);
    }

    /* ── 淡入淡出 ────────────────────────────────────────────────────────── */
    .bubble-fade-enter-active {
        transition: opacity 0.2s ease, transform 0.2s ease;
    }
    .bubble-fade-leave-active {
        transition: opacity 0.35s ease, transform 0.35s ease;
    }
    .bubble-fade-enter-from {
        opacity: 0;
        transform: translateY(4px) scale(0.97);
    }
    .bubble-fade-leave-to {
        opacity: 0;
        transform: translateY(-3px) scale(0.97);
    }
</style>