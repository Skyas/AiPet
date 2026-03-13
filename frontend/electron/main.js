const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, nativeImage } = require('electron')
const path = require('path')

const isDev = process.env.NODE_ENV !== 'production'

let mainWindow = null
let tray = null
let alwaysOnTopState = true  // 主进程维护置顶状态，与前端设置同步

function createTrayIcon() {
    const size = 16
    const buf = Buffer.alloc(size * size * 4)
    for (let i = 0; i < size * size; i++) {
        buf[i * 4 + 0] = 139
        buf[i * 4 + 1] = 92
        buf[i * 4 + 2] = 246
        buf[i * 4 + 3] = 255
    }
    return nativeImage.createFromBuffer(buf, { width: size, height: size })
}

function showWindow() {
    if (!mainWindow) return
    // 只在真正最小化时才 restore，避免触发 Electron 的尺寸重置
    if (mainWindow.isMinimized()) mainWindow.restore()
    // 使用主进程记录的状态，而不是硬编码 true
    mainWindow.setAlwaysOnTop(alwaysOnTopState, 'screen-saver')
    mainWindow.show()
    mainWindow.focus()
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 320,
        height: 480,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: true,
        skipTaskbar: false,  // 保留任务栏图标
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    })

    if (isDev) {
        mainWindow.loadURL('http://localhost:5173')
        mainWindow.webContents.openDevTools({ mode: 'detach' })
    } else {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
    }

    // 只拦截关闭，改为隐藏到托盘
    mainWindow.on('close', (e) => {
        e.preventDefault()
        mainWindow.hide()
    })

    // 不再拦截 minimize，让 Windows 正常处理最小化（任务栏图标保留）
    // 用户点任务栏图标可以正常最小化/还原，托盘图标始终可以唤醒

    mainWindow.on('closed', () => {
        mainWindow = null
    })
}

function createTray() {
    tray = new Tray(createTrayIcon())
    const contextMenu = Menu.buildFromTemplate([
        { label: 'Show AiPet', click: () => showWindow() },
        { label: 'Hide', click: () => mainWindow && mainWindow.hide() },
        { type: 'separator' },
        {
            label: 'Settings', click: () => {
                showWindow()
                setTimeout(() => mainWindow && mainWindow.webContents.send('navigate', '/settings'), 200)
            }
        },
        { type: 'separator' },
        { label: 'Quit', click: () => { mainWindow = null; app.exit(0) } }
    ])
    tray.setToolTip('AiPet')
    tray.setContextMenu(contextMenu)
    tray.on('click', () => {
        if (mainWindow && mainWindow.isVisible() && !mainWindow.isMinimized()) {
            mainWindow.hide()
        } else {
            showWindow()
        }
    })
}

ipcMain.handle('window-toggle', () => {
    if (mainWindow && mainWindow.isVisible() && !mainWindow.isMinimized()) {
        mainWindow.hide()
    } else {
        showWindow()
    }
})

ipcMain.handle('window-set-size', (_, { width, height }) => {
    mainWindow && mainWindow.setSize(width, height, true)
})

ipcMain.handle('window-set-opacity', (_, opacity) => {
    mainWindow && mainWindow.setOpacity(opacity)
})

// 更新置顶状态时同步到主进程变量，确保下次唤醒时行为一致
ipcMain.handle('window-set-always-on-top', (_, flag) => {
    alwaysOnTopState = flag
    if (mainWindow) {
        mainWindow.setAlwaysOnTop(flag, 'screen-saver')
    }
})

ipcMain.handle('get-backend-url', () => 'http://localhost:8001')

app.whenReady().then(() => {
    createWindow()
    createTray()
    globalShortcut.register('CommandOrControl+Shift+A', () => {
        if (mainWindow && mainWindow.isVisible() && !mainWindow.isMinimized()) {
            mainWindow.hide()
        } else {
            showWindow()
        }
    })
})

app.on('window-all-closed', () => {
    if (process.platform === 'darwin') app.quit()
})

app.on('will-quit', () => {
    globalShortcut.unregisterAll()
})