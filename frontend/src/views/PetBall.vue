<template>
    <div class="root" ref="rootEl">

        <!-- 悬浮工具栏（hover 时淡入，位于球上方） -->
        <transition name="fade">
            <div class="toolbar" v-if="showToolbar">
                <button class="tb-btn" @click="doExitBallMode" title="展开主窗口">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <rect x="1" y="1" width="14" height="14" rx="2.5" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M4 4h3M4 4v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                        <path d="M12 12h-3M12 12v-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span class="tb-label">展开</span>
                </button>

                <button class="tb-btn" :class="{ loading: isAnalyzing }"
                        :disabled="isAnalyzing" @click="doAnalyze" title="分析当前画面">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" :class="{ spin: isAnalyzing }">
                        <rect x="1" y="3" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/>
                        <circle cx="8" cy="8" r="2.5" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M5.5 1.5h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span class="tb-label">截图</span>
                </button>

                <button class="tb-btn" :class="{ active: proactiveRunning }"
                        @click="doToggleProactive" title="陪玩模式">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <rect x="1" y="4" width="14" height="9" rx="2" stroke="currentColor" stroke-width="1.5"/>
                        <circle cx="5.5" cy="8.5" r="1.2" fill="currentColor"/>
                        <circle cx="10.5" cy="8.5" r="1.2" fill="currentColor"/>
                        <path d="M8 2v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span class="tb-label">陪玩</span>
                </button>

                <button class="tb-btn tb-btn--off" disabled title="语音（即将开放）">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <rect x="5.5" y="1" width="5" height="8" rx="2.5" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M3 8a5 5 0 0 0 10 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                        <path d="M8 13v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span class="tb-label">语音</span>
                </button>

                <button class="tb-btn tb-btn--off" disabled title="QQ（即将开放）">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M8 2C5 2 3 4.5 3 7c0 1.2.3 2.3.9 3.1L3 13l2.5-.8C6.3 12.7 7.1 13 8 13s1.7-.3 2.5-.8l2.5.8-.9-2.9c.6-.8.9-1.9.9-3.1C13 4.5 11 2 8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                    </svg>
                    <span class="tb-label">QQ</span>
                </button>
            </div>
        </transition>

        <!-- 悬浮球 -->
        <div class="ball-wrap">
            <div class="ball"
                 :class="{ proactive: proactiveRunning, analyzing: isAnalyzing }"
                 ref="ballEl"
                 @dblclick="doExitBallMode"
                 @mousedown.left="startDrag">
                <!-- 简单的"脸"：两只眼睛 + 小嘴 -->
                <div class="face">
                    <div class="eyes">
                        <div class="eye" :class="{ blink }"></div>
                        <div class="eye" :class="{ blink }"></div>
                    </div>
                    <div class="mouth" :class="{ happy: proactiveRunning }"></div>
                </div>
                <!-- 陪玩模式光圈 -->
                <div class="ring" v-if="proactiveRunning"></div>
            </div>
        </div>

    </div>
</template>

<script setup>
    import { ref, onMounted, onUnmounted } from 'vue'
    import { screenAPI } from '@/utils/api'
    import { useSocket } from '@/utils/socket'

    const { socket } = useSocket()
    const rootEl         = ref(null)
    const ballEl         = ref(null)
    const showToolbar    = ref(false)
    const isAnalyzing    = ref(false)
    const proactiveRunning = ref(false)
    const blink          = ref(false)

    // ── 随机眨眼 ──────────────────────────────────────────────────────────────
    let blinkTimer = null
    function scheduleBlink() {
        blinkTimer = setTimeout(() => {
            blink.value = true
            setTimeout(() => { blink.value = false; scheduleBlink() }, 180)
        }, 2000 + Math.random() * 3000)
    }

    // ── 鼠标悬停检测（配合 forward:true 的 click-through）────────────────────
    function isOverInteractive(e) {
        const targets = rootEl.value?.querySelectorAll('.ball, .toolbar')
        if (!targets) return false
        for (const el of targets) {
            if (!el.offsetParent && el.style.display === 'none') continue
            const r = el.getBoundingClientRect()
            if (e.clientX >= r.left && e.clientX <= r.right &&
                e.clientY >= r.top  && e.clientY <= r.bottom) return true
        }
        return false
    }

    function onRootMouseMove(e) {
        const over = isOverInteractive(e)
        window.electronAPI?.setBallIgnoreMouse(!over)
        showToolbar.value = over
    }

    // ── 拖拽（主进程轮询 getCursorScreenPoint，不受渲染层 mousemove 中断影响）──
    function startDrag() {
        window.electronAPI?.ballDragStart()
        // 临时关闭 ignore-mouse 确保 mouseup 能被捕获
        window.electronAPI?.setBallIgnoreMouse(false)
        window.addEventListener('mouseup', stopDrag, { once: true })
    }

    function stopDrag() {
        window.electronAPI?.ballDragStop()
        // 交还穿透状态给 hover 逻辑接管
        window.electronAPI?.setBallIgnoreMouse(!showToolbar.value)
    }

    // ── 操作 ──────────────────────────────────────────────────────────────────
    function doExitBallMode() {
        window.electronAPI?.exitBallMode()
    }

    async function doAnalyze() {
        if (isAnalyzing.value) return
        isAnalyzing.value = true

        const placeholder = '👁 正在分析当前画面...'
        await window.electronAPI?.showBubble(placeholder)

        let result = ''
        await screenAPI.analyze({
            onToken(t) { result += t },
            async onDone() {
                isAnalyzing.value = false
                if (result) {
                    // 气泡显示结果
                    window.electronAPI?.showBubble(result)
                    // 同步写入主窗口聊天历史
                    window.electronAPI?.relayMessageToMain({
                        role: 'assistant', content: result, proactive: false,
                    })
                }
            },
            onError(e) {
                isAnalyzing.value = false
                window.electronAPI?.showBubble(`[分析失败] ${e}`)
            },
        })
    }

    async function doToggleProactive() {
        if (proactiveRunning.value) {
            await screenAPI.stopProactive()
            proactiveRunning.value = false
        } else {
            await screenAPI.startProactive()
            proactiveRunning.value = true
        }
    }

    // ── 主动消息推送（球模式下也要更新状态）──────────────────────────────────
    function handleProactiveMessage(data) {
        window.electronAPI?.showBubble(data.content)
        window.electronAPI?.relayMessageToMain({
            role: 'assistant', content: data.content, proactive: true,
        })
    }

    // ── 生命周期 ──────────────────────────────────────────────────────────────
    onMounted(async () => {
        // 根据 DPI 设置球体尺寸 CSS 变量
        try {
            const sz = await window.electronAPI.getBallSize()
            document.documentElement.style.setProperty('--ball-sz', sz + 'px')
        } catch {}

        // 同步陪玩引擎状态
        try {
            const status = await screenAPI.getStatus()
            proactiveRunning.value = status.proactive_running ?? false
        } catch {}

        window.addEventListener('mousemove', onRootMouseMove)
        socket?.on('proactive_message', handleProactiveMessage)
        scheduleBlink()
    })

    onUnmounted(() => {
        window.removeEventListener('mousemove', onRootMouseMove)
        window.electronAPI?.ballDragStop()   // 确保主进程 interval 被清理
        socket?.off('proactive_message', handleProactiveMessage)
        clearTimeout(blinkTimer)
    })
</script>

<style scoped>
    /* 根容器：透明，不干扰点击 */
    .root {
        width: 100vw;
        height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-end;
        padding-bottom: 10px;
        background: transparent;
        user-select: none;
        -webkit-user-select: none;
    }

    /* ── 悬浮工具栏 ────────────────────────────────────────────────────────── */
    .toolbar {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 5px 7px;
        margin-bottom: 6px;
        background: rgba(12, 10, 24, 0.82);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        backdrop-filter: blur(6px);
    }

    .tb-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        width: 30px;
        height: 34px;
        border: none;
        border-radius: 7px;
        background: transparent;
        color: #888;
        cursor: pointer;
        transition: background 0.15s, color 0.15s;
        padding: 4px 0;
    }
    .tb-btn:hover:not(:disabled) {
        background: rgba(255,255,255,0.09);
        color: #ccc;
    }
    .tb-btn.active {
        background: rgba(56,189,248,0.15);
        color: #38bdf8;
    }
    .tb-btn.loading {
        color: #fcd34d;
    }
    .tb-btn--off {
        opacity: 0.2;
        cursor: not-allowed;
    }

    .tb-label {
        font-size: 9px;
        letter-spacing: 0.02em;
        font-family: system-ui, sans-serif;
        line-height: 1;
    }

    /* 旋转动画（分析中） */
    .spin {
        animation: spin 1s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* 淡入淡出 */
    .fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
    .fade-enter-from, .fade-leave-to { opacity: 0; }

    /* ── 球体 ───────────────────────────────────────────────────────────────── */
    .ball-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        /* 球的可见尺寸由 CSS var 控制，默认 56px */
    }

    .ball {
        width:  var(--ball-sz, 56px);
        height: var(--ball-sz, 56px);
        border-radius: 50%;
        background: #0d0c1e;
        border: 1.5px solid rgba(139,92,246,0.35);
        cursor: grab;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: border-color 0.25s, box-shadow 0.25s;
        overflow: hidden;
    }
    .ball:active { cursor: grabbing; }

    /* 陪玩模式：青蓝边框 + 外发光 */
    .ball.proactive {
        border-color: rgba(56,189,248,0.6);
        box-shadow: 0 0 10px rgba(56,189,248,0.25), 0 0 20px rgba(56,189,248,0.1);
    }

    /* 分析中：琥珀色脉冲 */
    .ball.analyzing {
        border-color: rgba(250,204,21,0.5);
        animation: pulse-amber 1s ease-in-out infinite;
    }
    @keyframes pulse-amber {
        0%,100% { box-shadow: 0 0 6px rgba(250,204,21,0.2); }
        50%      { box-shadow: 0 0 14px rgba(250,204,21,0.45); }
    }

    /* 陪玩光圈 */
    .ring {
        position: absolute;
        inset: -5px;
        border-radius: 50%;
        border: 1.5px solid rgba(56,189,248,0.25);
        animation: ring-pulse 2s ease-in-out infinite;
        pointer-events: none;
    }
    @keyframes ring-pulse {
        0%,100% { opacity: 0.6; transform: scale(1); }
        50%      { opacity: 0.2; transform: scale(1.12); }
    }

    /* ── 小脸 ───────────────────────────────────────────────────────────────── */
    .face {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 5px;
    }

    .eyes {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .eye {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #38bdf8;
        transition: height 0.1s;
    }
    .eye.blink {
        height: 1.5px;
    }
    .ball.proactive .eye {
        background: #7dd3fc;
        box-shadow: 0 0 4px #38bdf8;
    }

    .mouth {
        width: 10px;
        height: 5px;
        border-bottom: 1.5px solid rgba(139,92,246,0.6);
        border-left:   1.5px solid transparent;
        border-right:  1.5px solid transparent;
        border-radius: 0 0 6px 6px;
        transition: border-color 0.25s;
    }
    .mouth.happy {
        border-bottom-color: rgba(56,189,248,0.8);
    }
</style>