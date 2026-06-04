<template>
  <div class="page">
    <h1>✍️ 文案管理</h1>
    <p class="subtitle">AI 生成分镜脚本</p>

    <div class="card">
      <div class="form-row">
        <label>话题：</label>
        <input v-model="topic" placeholder="输入话题..." style="flex:1" />
      </div>
      <div class="form-row">
        <label>人设：</label>
        <select v-model="persona">
          <option value="知识科普博主">知识科普博主</option>
          <option value="生活技巧博主">生活技巧博主</option>
          <option value="科技资讯博主">科技资讯博主</option>
          <option value="情感故事博主">情感故事博主</option>
        </select>
        <label>分镜数：</label>
        <input v-model.number="sceneCount" type="number" min="1" max="10" style="width:60px" />
        <button class="btn btn-primary" @click="generate" :disabled="loading || !topic">
          {{ loading ? '生成中...' : '✍️ 生成文案' }}
        </button>
      </div>
    </div>

    <div class="loading" v-if="loading">MiMo API 生成中，请稍候...</div>

    <!-- 当前脚本 -->
    <div class="card" v-if="currentScript">
      <h3>{{ currentScript.topic }} — {{ currentScript.persona }}</h3>
      <div class="scene" v-for="s in currentScript.scenes" :key="s.scene_id">
        <div class="scene-header">分镜 {{ s.scene_id }}</div>
        <div class="scene-body">
          <p><strong>配文：</strong>{{ s.narration }}</p>
          <p class="prompt"><strong>Prompt：</strong>{{ s.image_prompt }}</p>
          <div class="tags">
            <span class="tag" v-for="k in s.style_keywords" :key="k">{{ k }}</span>
          </div>
        </div>
      </div>
      <div style="margin-top:16px">
        <button class="btn btn-primary" @click="goImages">🖼️ 生成图片</button>
      </div>
    </div>

    <!-- 历史列表 -->
    <div class="card" v-if="history.length">
      <h3>历史脚本 ({{ history.length }})</h3>
      <table>
        <thead><tr><th>文件名</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="f in history" :key="f">
            <td>{{ f }}</td>
            <td><button class="btn btn-secondary" @click="loadScript(f)" style="padding:4px 12px;font-size:12px">查看</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const topic = ref(route.query.topic || '')
const persona = ref('知识科普博主')
const sceneCount = ref(5)
const loading = ref(false)
const currentScript = ref(null)
const history = ref([])

async function generate() {
  loading.value = true
  try {
    const res = await api.generateScript({ topic: topic.value, persona: persona.value, scene_count: sceneCount.value })
    currentScript.value = res.script
    loadHistory()
  } catch (e) { alert('生成失败: ' + e.message) }
  finally { loading.value = false }
}

async function loadScript(filename) {
  try {
    const data = await api.getScript(filename)
    currentScript.value = data
  } catch (e) { alert('加载失败: ' + e.message) }
}

async function loadHistory() {
  try {
    const res = await api.listScripts()
    history.value = res.scripts || []
  } catch (e) { /* ignore */ }
}

function goImages() {
  router.push('/images')
}

onMounted(loadHistory)
</script>

<style scoped>
.form-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.form-row label { font-size: 14px; white-space: nowrap; }
.scene { background: #fafafa; border-radius: 6px; padding: 16px; margin-bottom: 12px; }
.scene-header { font-weight: 600; margin-bottom: 8px; color: #1976d2; }
.scene-body p { margin-bottom: 6px; font-size: 14px; }
.prompt { color: #666; font-size: 13px; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
</style>