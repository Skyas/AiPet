const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, nativeImage } = require('electron')
const path = require('path')

const isDev = process.env.NODE_ENV !== 'production'

let mainWindow = null
let tray = null

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
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.setAlwaysOnTop(true)
  mainWindow.show()
  mainWindow.focus()
  setTimeout(() => {
    if (mainWindow) mainWindow.setAlwaysOnTop(true)
  }, 100)
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 320,
    height: 480,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    skipTaskbar: true,
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

  mainWindow.on('close', (e) => {
    e.preventDefault()
    mainWindow.hide()
  })

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
    { label: 'Settings', click: () => {
      showWindow()
      setTimeout(() => {
        mainWindow && mainWindow.webContents.send('navigate', '/settings')
      }, 200)
    }},
    { type: 'separator' },
    { label: 'Quit', click: () => {
      mainWindow = null
      app.exit(0)
    }}
  ])

  tray.setToolTip('AiPet')
  tray.setContextMenu(contextMenu)
  tray.on('click', () => {
    if (mainWindow && mainWindow.isVisible()) {
      mainWindow.hide()
    } else {
      showWindow()
    }
  })
}

ipcMain.handle('window-toggle', () => {
  if (mainWindow && mainWindow.isVisible()) {
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

ipcMain.handle('get-backend-url', () => 'http://localhost:8001')

app.whenReady().then(() => {
  createWindow()
  createTray()
  globalShortcut.register('CommandOrControl+Shift+A', () => {
    if (mainWindow && mainWindow.isVisible()) {
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