import { createRouter, createWebHashHistory } from 'vue-router'
import ChatPanel from '@/views/ChatPanel.vue'
import SettingsPanel from '@/views/SettingsPanel.vue'
import PromptEditor from '@/views/PromptEditor.vue'

const routes = [
  { path: '/', component: ChatPanel },
  { path: '/settings', component: SettingsPanel },
  { path: '/prompts', component: PromptEditor },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
