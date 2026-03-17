const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, nativeImage, screen } = require('electron')
const path = require('path')
const fs   = require('fs')

const isDev = process.env.NODE_ENV !== 'production'

let mainWindow    = null
let petBallWindow = null
let bubbleWindow  = null
let tray          = null
let alwaysOnTopState = true
let isBallMode       = false

// ── Position persistence ──────────────────────────────────────────────────────
const posFile = path.join(app.getPath('userData'), 'ball-position.json')

function loadBallPosition() {
    try { return JSON.parse(fs.readFileSync(posFile, 'utf-8')) } catch { return null }
}
function saveBallPosition(x, y) {
    try { fs.writeFileSync(posFile, JSON.stringify({ x, y })) } catch {}
}

// ── DPI-aware ball size ───────────────────────────────────────────────────────
function getBallSize() {
    const { scaleFactor } = screen.getPrimaryDisplay()
    if (scaleFactor <= 1.25) return 52
    if (scaleFactor <= 1.75) return 56
    return 62
}

// ── Tray icon ─────────────────────────────────────────────────────────────────
function createTrayIcon() {
    const size = 16
    const buf = Buffer.alloc(size * size * 4)
    for (let i = 0; i < size * size; i++) {
        buf[i * 4 + 0] = 139; buf[i * 4 + 1] = 92
        buf[i * 4 + 2] = 246; buf[i * 4 + 3] = 255
    }
    return nativeImage.createFromBuffer(buf, { width: size, height: size })
}

// ── Bubble positioning ────────────────────────────────────────────────────────
function positionBubble() {
    if (!petBallWindow || !bubbleWindow) return
    const [bx, by]      = petBallWindow.getPosition()
    const [bw, bh]      = petBallWindow.getSize()
    const { workArea }  = screen.getPrimaryDisplay()
    const bubbleW = 260
    const bubbleH = 120

    // Ball circle sits at the bottom of petBallWindow (toolbar above it)
    const TOOLBAR_H = 50
    const ballCenterX = bx + Math.round(bw / 2)
    const ballTopY    = by + TOOLBAR_H

    let bubbleX      = ballCenterX - Math.round(bubbleW / 2)
    let bubbleY      = ballTopY - bubbleH - 6
    let tailAtBottom = true   // tail points downward (bubble above ball)

    if (bubbleY < workArea.y) {
        // Not enough space above → show below
        bubbleY      = by + bh + 6
        tailAtBottom = false
    }

    // Clamp X within work area
    bubbleX = Math.max(workArea.x + 8,
              Math.min(bubbleX, workArea.x + workArea.width - bubbleW - 8))

    bubbleWindow.setPosition(Math.round(bubbleX), Math.round(bubbleY))

    // Tell bubble where the tail should be (px from left edge of bubble)
    const tailX = Math.max(20, Math.min(ballCenterX - bubbleX, bubbleW - 20))
    bubbleWindow.webContents.send('bubble-tail', { tailAtBottom, tailX })
}

// ── Main window ───────────────────────────────────────────────────────────────
function showWindow() {
    if (!mainWindow) return
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.setAlwaysOnTop(alwaysOnTopState, 'screen-saver')
    mainWindow.show()
    mainWindow.focus()
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 320, height: 480,
        frame: false, transparent: true,
        alwaysOnTop: true, resizable: true, skipTaskbar: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true, nodeIntegration: false,
        },
    })

    if (isDev) {
        mainWindow.loadURL('http://localhost:5173')
        mainWindow.webContents.openDevTools({ mode: 'detach' })
    } else {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
    }

    mainWindow.on('close', (e) => { e.preventDefault(); mainWindow.hide() })
    mainWindow.on('closed', () => { mainWindow = null })
}

// ── Pet ball window ───────────────────────────────────────────────────────────
const TOOLBAR_H  = 50   // toolbar area height above the ball
const BALL_PAD_B = 10   // bottom padding

function createPetBallWindow() {
    const ballSize = getBallSize()
    const winW = 200
    const winH = TOOLBAR_H + ballSize + BALL_PAD_B

    const { workArea } = screen.getPrimaryDisplay()
    const saved = loadBallPosition()
    const x = saved?.x ?? (workArea.x + workArea.width  - winW - 20)
    const y = saved?.y ?? (workArea.y + workArea.height - winH - 20)

    petBallWindow = new BrowserWindow({
        width: winW, height: winH, x, y,
        frame: false, transparent: true,
        alwaysOnTop: true, skipTaskbar: true, resizable: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true, nodeIntegration: false,
        },
    })

    // Fully click-through by default; renderer toggles when hovered
    petBallWindow.setIgnoreMouseEvents(true, { forward: true })

    if (isDev) {
        petBallWindow.loadURL('http://localhost:5173/#/pet-ball')
    } else {
        petBallWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: '/pet-ball' })
    }

    petBallWindow.on('closed', () => { petBallWindow = null })
}

// ── Bubble window ─────────────────────────────────────────────────────────────
function createBubbleWindow() {
    bubbleWindow = new BrowserWindow({
        width: 260, height: 120,
        frame: false, transparent: true,
        alwaysOnTop: true, skipTaskbar: true, resizable: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true, nodeIntegration: false,
        },
    })

    // Bubble is always fully click-through (no interaction needed)
    bubbleWindow.setIgnoreMouseEvents(true)

    if (isDev) {
        bubbleWindow.loadURL('http://localhost:5173/#/bubble')
    } else {
        bubbleWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: '/bubble' })
    }

    bubbleWindow.hide()
    bubbleWindow.on('closed', () => { bubbleWindow = null })
}

// ── Tray ──────────────────────────────────────────────────────────────────────
function createTray() {
    tray = new Tray(createTrayIcon())
    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Show AiPet', click: () => {
                if (isBallMode) exitBallMode()
                else showWindow()
            }
        },
        { label: 'Hide', click: () => mainWindow && mainWindow.hide() },
        { type: 'separator' },
        {
            label: 'Settings', click: () => {
                if (isBallMode) exitBallMode()
                showWindow()
                setTimeout(() => mainWindow?.webContents.send('navigate', '/settings'), 200)
            }
        },
        { type: 'separator' },
        { label: 'Quit', click: () => { mainWindow = null; app.exit(0) } }
    ])
    tray.setToolTip('AiPet')
    tray.setContextMenu(contextMenu)
    tray.on('click', () => {
        if (isBallMode) { exitBallMode(); return }
        if (mainWindow?.isVisible() && !mainWindow.isMinimized()) mainWindow.hide()
        else showWindow()
    })
}

// ── Exit ball mode ────────────────────────────────────────────────────────────
function exitBallMode() {
    isBallMode = false
    petBallWindow?.hide()
    bubbleWindow?.hide()
    showWindow()
}

// ── IPC: existing ─────────────────────────────────────────────────────────────
ipcMain.handle('window-toggle', () => {
    if (isBallMode) { exitBallMode(); return }
    if (mainWindow?.isVisible() && !mainWindow.isMinimized()) mainWindow.hide()
    else showWindow()
})

ipcMain.handle('window-set-size', (_, { width, height }) => {
    mainWindow?.setSize(width, height, true)
})

ipcMain.handle('window-set-opacity', (_, opacity) => {
    mainWindow?.setOpacity(opacity)
})

ipcMain.handle('window-set-always-on-top', (_, flag) => {
    alwaysOnTopState = flag
    mainWindow?.setAlwaysOnTop(flag, 'screen-saver')
})

ipcMain.handle('get-backend-url', () => 'http://localhost:8001')

// ── IPC: ball mode ────────────────────────────────────────────────────────────
ipcMain.handle('enter-ball-mode', () => {
    isBallMode = true
    mainWindow?.hide()
    if (!petBallWindow) createPetBallWindow()
    else petBallWindow.show()
    if (!bubbleWindow) createBubbleWindow()
    else bubbleWindow.hide()
})

ipcMain.handle('exit-ball-mode', () => {
    exitBallMode()
})

// Renderer toggles click-through based on hover state
ipcMain.handle('ball-set-ignore-mouse', (_, ignore) => {
    petBallWindow?.setIgnoreMouseEvents(ignore, { forward: true })
})

// ── Main-process drag (polling cursor, immune to renderer mousemove gaps) ────
let dragInterval    = null
let dragOffsetX     = 0
let dragOffsetY     = 0

ipcMain.handle('ball-drag-start', () => {
    if (!petBallWindow || dragInterval) return
    const cursor    = screen.getCursorScreenPoint()
    const [wx, wy]  = petBallWindow.getPosition()
    dragOffsetX     = cursor.x - wx
    dragOffsetY     = cursor.y - wy

    dragInterval = setInterval(() => {
        if (!petBallWindow) { clearInterval(dragInterval); dragInterval = null; return }
        const cur = screen.getCursorScreenPoint()
        const { workArea } = screen.getPrimaryDisplay()
        const [w, h] = petBallWindow.getSize()
        const nx = Math.max(workArea.x, Math.min(cur.x - dragOffsetX, workArea.x + workArea.width  - w))
        const ny = Math.max(workArea.y, Math.min(cur.y - dragOffsetY, workArea.y + workArea.height - h))
        petBallWindow.setPosition(Math.round(nx), Math.round(ny))
    }, 16)   // ~60 fps
})

ipcMain.handle('ball-drag-stop', () => {
    if (dragInterval) { clearInterval(dragInterval); dragInterval = null }
    if (!petBallWindow) return
    const [x, y] = petBallWindow.getPosition()
    saveBallPosition(x, y)
})

ipcMain.handle('ball-get-pos', () => {
    if (!petBallWindow) return null
    const [x, y] = petBallWindow.getPosition()
    const [w, h] = petBallWindow.getSize()
    return { x, y, w, h }
})

ipcMain.handle('get-ball-size', () => getBallSize())

ipcMain.handle('get-screen-workarea', () => screen.getPrimaryDisplay().workArea)

// ── IPC: bubble ───────────────────────────────────────────────────────────────
ipcMain.handle('show-bubble', (_, { text }) => {
    if (!isBallMode) return
    if (!bubbleWindow) createBubbleWindow()
    positionBubble()
    bubbleWindow.show()
    bubbleWindow.webContents.send('bubble-content', { text })
})

ipcMain.handle('hide-bubble', () => {
    bubbleWindow?.hide()
})

// ── IPC: right-click context menu for ChatPanel ──────────────────────────────
ipcMain.handle('chat-context-menu', (event) => {
    const { Menu } = require('electron')
    const win = BrowserWindow.fromWebContents(event.sender)
    Menu.buildFromTemplate([
        {
            label: '收起窗口',
            click: () => win?.hide()
        },
        { type: 'separator' },
        {
            label: '清空对话',
            click: () => win?.webContents.send('context-action', 'clear')
        },
    ]).popup({ window: win })
})

// ── IPC: relay message to main window (from pet ball analysis) ────────────────
ipcMain.handle('relay-message-to-main', (_, msg) => {
    mainWindow?.webContents.send('add-message', msg)
})

// ── App bootstrap ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
    createWindow()
    createTray()
    globalShortcut.register('CommandOrControl+Shift+A', () => {
        if (isBallMode) { exitBallMode(); return }
        if (mainWindow?.isVisible() && !mainWindow.isMinimized()) mainWindow.hide()
        else showWindow()
    })
})

app.on('window-all-closed', () => {
    if (process.platform === 'darwin') app.quit()
})

app.on('will-quit', () => {
    globalShortcut.unregisterAll()
})