import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

const api = {}

const irisAPI = {
  startSession: () => {
    ipcRenderer.send('iris:start-session')
  },

  getHistory: () => ipcRenderer.invoke('iris:get-history'),
  stopSession: () => ipcRenderer.send('iris:stop-session'),
  toggleMic: (isMuted: boolean) => ipcRenderer.send('iris:toggle-mic', isMuted),

  onSystemStatus: (callback: (status: string) => void) => {
    ipcRenderer.on('iris:system-status', (_event, status) => callback(status))
  },

  onSpeakingState: (callback: (isSpeaking: boolean) => void) => {
    ipcRenderer.on('iris:speaking-state', (_event, isSpeaking) => callback(isSpeaking))
  },

  onTranscript: (callback: (data: any) => void) => {
    ipcRenderer.removeAllListeners('iris:transcript')
    ipcRenderer.on('iris:transcript', (_event, data) => callback(data))
  },

  onTranscriptComplete: (callback: () => void) => {
    ipcRenderer.removeAllListeners('iris:transcript-complete')
    ipcRenderer.on('iris:transcript-complete', () => callback())
  },

  sendVisionFrame: (base64Frame: string) => ipcRenderer.send('iris:send-vision-frame', base64Frame),

  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('iris:system-status')
    ipcRenderer.removeAllListeners('iris:speaking-state')
    ipcRenderer.removeAllListeners('iris:transcript')
    ipcRenderer.removeAllListeners('iris:transcript-complete')
  }
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', {
      ...electronAPI,
      ipcRenderer: {
        ...electronAPI.ipcRenderer,
        invoke: (channel: string, ...args: any[]) => ipcRenderer.invoke(channel, ...args)
      }
    })
    contextBridge.exposeInMainWorld('api', api)

    contextBridge.exposeInMainWorld('iris', irisAPI)
  } catch (error) {}
} else {
  // @ts-ignore (define in dts)
  window.electron = {
    ...electronAPI,
    ipcRenderer: {
      ...electronAPI.ipcRenderer,
      invoke: ipcRenderer.invoke.bind(ipcRenderer)
    }
  }
  // @ts-ignore (define in dts)
  window.api = api
}
