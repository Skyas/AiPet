import { defineStore } from 'pinia'
import { settingsAPI } from '@/utils/api'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    config: null,
    loaded: false,
  }),

  actions: {
    async load() {
      try {
        const res = await settingsAPI.get()
        this.config = res.data
        this.loaded = true
      } catch (e) {
        console.error('加载配置失败', e)
      }
    },

    async update(partial) {
      try {
        const res = await settingsAPI.update(partial)
        this.config = res.data.config
      } catch (e) {
        console.error('保存配置失败', e)
      }
    },
  },

  getters: {
    voiceEnabled: (s) => s.config?.voice?.enabled ?? false,
    qqEnabled: (s) => s.config?.qq?.enabled ?? false,
  }
})
