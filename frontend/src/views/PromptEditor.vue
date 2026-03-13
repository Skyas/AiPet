<template>
  <div class="prompts-panel">
    <div class="titlebar" style="-webkit-app-region: drag">
      <span class="title">🎭 Prompt 卡片</span>
      <button class="icon-btn" style="-webkit-app-region: no-drag" @click="goBack">✕</button>
    </div>

    <div class="content">
      <!-- 卡片列表 -->
      <div v-if="!editing" class="list-view">
        <button class="btn-primary" @click="newPrompt">+ 新建角色卡</button>
        <div class="prompt-list">
          <div
            v-for="p in prompts"
            :key="p.id"
            class="prompt-item"
            :class="{ active: activeChatStore.promptId === p.id }"
          >
            <div class="prompt-info" @click="selectPrompt(p.id)">
              <div class="prompt-name">{{ p.name }}</div>
              <div class="prompt-desc">{{ p.description }}</div>
            </div>
            <div class="prompt-actions">
              <button @click="editPrompt(p)" title="编辑">✏</button>
              <button @click="deletePrompt(p)" title="删除" :disabled="p.id === 'default_assistant'">🗑</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 编辑器 -->
      <div v-else class="editor-view">
        <div class="editor-header">
          <button class="back-btn" @click="goBack">← 返回</button>
          <button class="btn-primary small" @click="savePrompt">保存</button>
        </div>
        <label class="field">
          <span>名称</span>
          <input v-model="form.name" placeholder="角色名称" />
        </label>
        <label class="field">
          <span>描述</span>
          <input v-model="form.description" placeholder="简短描述" />
        </label>
        <label class="field">
          <span>System Prompt</span>
          <textarea v-model="form.system_prompt" rows="6" placeholder="你是一个..." />
        </label>
        <label class="field">
          <span>问候语</span>
          <input v-model="form.greeting" placeholder="第一条消息" />
        </label>
        <label class="field">
          <span>标签（逗号分隔）</span>
          <input v-model="tagsInput" placeholder="通用, 游戏" />
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { promptsAPI } from '@/utils/api'
import { useChatStore } from '@/stores/chat'

const router = useRouter()
const activeChatStore = useChatStore()
const prompts = ref([])
const editing = ref(false)
const form = ref({})
const tagsInput = ref('')

function goBack() {
  if (editing.value) {
    editing.value = false
  } else {
    router.replace('/settings')
  }
}

async function loadPrompts() {
  const res = await promptsAPI.list()
  prompts.value = res.data.prompts
}

function newPrompt() {
  form.value = { name: '', description: '', system_prompt: '', greeting: '', tags: [] }
  tagsInput.value = ''
  editing.value = true
}

function editPrompt(p) {
  form.value = { ...p }
  tagsInput.value = (p.tags || []).join(', ')
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function savePrompt() {
  form.value.tags = tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  await promptsAPI.save(form.value)
  await loadPrompts()
  editing.value = false
}

async function deletePrompt(p) {
  if (p.id === 'default_assistant') return
  if (confirm('Delete ' + p.name + '?')) {
    await promptsAPI.delete(p.id)
    await loadPrompts()
  }
}

function selectPrompt(id) {
  activeChatStore.promptId = id
}

onMounted(loadPrompts)
</script>

<style scoped>
.prompts-panel {
  display: flex; flex-direction: column; height: 100vh;
  background: rgba(18, 18, 22, 0.95); backdrop-filter: blur(12px);
  border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);
  color: #e8e8ec; font-family: system-ui, sans-serif; overflow: hidden;
}
.titlebar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px 8px; border-bottom: 1px solid rgba(255,255,255,0.06);
}
.title { font-size: 14px; font-weight: 500; color: #c9b8f8; }
.icon-btn { background: none; border: none; color: #888; font-size: 14px; padding: 3px 8px; border-radius: 6px; cursor: pointer; }
.icon-btn:hover { background: rgba(255,255,255,0.08); color: #ddd; }
.content { flex: 1; overflow-y: auto; padding: 12px; }
.content::-webkit-scrollbar { width: 4px; }
.content::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

.btn-primary {
  background: rgba(139,92,246,0.5); border: 1px solid rgba(139,92,246,0.3);
  color: #fff; font-size: 12px; padding: 7px 14px; border-radius: 8px;
  cursor: pointer; width: 100%; margin-bottom: 10px;
}
.btn-primary:hover { background: rgba(139,92,246,0.7); }
.btn-primary.small { width: auto; padding: 5px 12px; margin-bottom: 0; }

.prompt-list { display: flex; flex-direction: column; gap: 6px; }
.prompt-item {
  display: flex; align-items: center; justify-content: space-between;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px; padding: 8px 10px; cursor: pointer;
}
.prompt-item.active { border-color: rgba(139,92,246,0.4); background: rgba(139,92,246,0.06); }
.prompt-info { flex: 1; }
.prompt-name { font-size: 13px; font-weight: 500; }
.prompt-desc { font-size: 11px; color: #666; margin-top: 2px; }
.prompt-actions { display: flex; gap: 4px; }
.prompt-actions button {
  background: none; border: none; color: #666; font-size: 13px;
  padding: 2px 5px; border-radius: 4px; cursor: pointer;
}
.prompt-actions button:hover { color: #aaa; background: rgba(255,255,255,0.06); }
.prompt-actions button:disabled { opacity: 0.2; cursor: not-allowed; }

.editor-view { display: flex; flex-direction: column; gap: 10px; }
.editor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.back-btn { background: none; border: none; color: #8b5cf6; font-size: 12px; cursor: pointer; padding: 0; }

.field { display: flex; flex-direction: column; gap: 4px; }
.field span { font-size: 11px; color: #888; }
.field input, .field textarea {
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; color: #e8e8ec; font-size: 12px; padding: 7px 10px;
  outline: none; font-family: inherit; resize: vertical;
}
.field input:focus, .field textarea:focus { border-color: rgba(139,92,246,0.4); }
</style>
