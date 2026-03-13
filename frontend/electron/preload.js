const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  toggleWindow: () => ipcRenderer.invoke('window-toggle'),
  setSize: (w, h) => ipcRenderer.invoke('window-set-size', { width: w, height: h }),
  setOpacity: (o) => ipcRenderer.invoke('window-set-opacity', o),
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  onNavigate: (cb) => ipcRenderer.on('navigate', (_, p) => cb(p)),
})
