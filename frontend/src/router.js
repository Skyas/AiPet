import { createRouter, createWebHashHistory } from 'vue-router'
import ChatPanel    from '@/views/ChatPanel.vue'
import SettingsPanel from '@/views/SettingsPanel.vue'
import PromptEditor  from '@/views/PromptEditor.vue'
import VisionPanel   from '@/views/VisionPanel.vue'
import PetBall       from '@/views/PetBall.vue'
import SpeechBubble  from '@/views/SpeechBubble.vue'

const routes = [
    { path: '/',          component: ChatPanel },
    { path: '/settings',  component: SettingsPanel },
    { path: '/prompts',   component: PromptEditor },
    { path: '/vision',    component: VisionPanel },
    { path: '/pet-ball',  component: PetBall },
    { path: '/bubble',    component: SpeechBubble },
]

export default createRouter({
    history: createWebHashHistory(),
    routes,
})