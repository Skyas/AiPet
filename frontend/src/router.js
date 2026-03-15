import { createRouter, createWebHashHistory } from 'vue-router'
import ChatPanel from '@/views/ChatPanel.vue'
import SettingsPanel from '@/views/SettingsPanel.vue'
import PromptEditor from '@/views/PromptEditor.vue'
import VisionPanel from '@/views/VisionPanel.vue'   // Phase 2 新增

const routes = [
    { path: '/', component: ChatPanel },
    { path: '/settings', component: SettingsPanel },
    { path: '/prompts', component: PromptEditor },
    { path: '/vision', component: VisionPanel },    // Phase 2 新增
]

export default createRouter({
    history: createWebHashHistory(),
    routes,
})