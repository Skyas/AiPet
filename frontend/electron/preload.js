const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
    // ── 已有 ─────────────────────────────────────────────────────────────────
    toggleWindow:    ()        => ipcRenderer.invoke('window-toggle'),
    setSize:         (w, h)    => ipcRenderer.invoke('window-set-size', { width: w, height: h }),
    setOpacity:      (o)       => ipcRenderer.invoke('window-set-opacity', o),
    setAlwaysOnTop:  (flag)    => ipcRenderer.invoke('window-set-always-on-top', flag),
    getBackendUrl:   ()        => ipcRenderer.invoke('get-backend-url'),
    onNavigate:      (cb)      => ipcRenderer.on('navigate', (_, p) => cb(p)),

    // ── 悬浮球模式 ───────────────────────────────────────────────────────────
    enterBallMode:       ()         => ipcRenderer.invoke('enter-ball-mode'),
    exitBallMode:        ()         => ipcRenderer.invoke('exit-ball-mode'),
    setBallIgnoreMouse:  (ignore)   => ipcRenderer.invoke('ball-set-ignore-mouse', ignore),
    ballDragStart:       ()         => ipcRenderer.invoke('ball-drag-start'),
    ballDragStop:        ()         => ipcRenderer.invoke('ball-drag-stop'),
    getBallPos:          ()         => ipcRenderer.invoke('ball-get-pos'),
    getBallSize:         ()         => ipcRenderer.invoke('get-ball-size'),
    getScreenWorkarea:   ()         => ipcRenderer.invoke('get-screen-workarea'),

    // ── 气泡 ─────────────────────────────────────────────────────────────────
    showBubble:      (text)    => ipcRenderer.invoke('show-bubble', { text }),
    hideBubble:      ()        => ipcRenderer.invoke('hide-bubble'),
    onBubbleContent: (cb)      => ipcRenderer.on('bubble-content', (_, d) => cb(d)),
    onBubbleTail:    (cb)      => ipcRenderer.on('bubble-tail',    (_, d) => cb(d)),

    // ── 跨窗口消息中转（球模式分析结果 → 主窗口历史）────────────────────────
    relayMessageToMain: (msg)  => ipcRenderer.invoke('relay-message-to-main', msg),
    showChatContextMenu: ()    => ipcRenderer.invoke('chat-context-menu'),
    onContextAction:     (cb)  => ipcRenderer.on('context-action', (_, a) => cb(a)),
    onAddMessage:       (cb)   => ipcRenderer.on('add-message', (_, d) => cb(d)),
})