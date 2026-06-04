<template>
  <div class="page">
    <h1>📊 仪表盘</h1>
    <p class="subtitle">流水线状态总览</p>

    <div class="grid grid-3">
      <div class="card stat-card">
        <div class="stat-label">流水线状态</div>
        <div class="stat-value">
          <span class="status" :class="'status-' + status.status">{{ statusText }}</span>
        </div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">已生成脚本</div>
        <div class="stat-value">{{ scripts.length }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">已生成图片组</div>
        <div class="stat-value">{{ imageDirs.length }}</div>
      </div>
    </div>

    <div class="card">
      <h3>⚡ 快速操作</h3>
      <div class="actions">
        <button class="btn btn-primary" @click="quickScrape" :disabled="loading">
          🔥 采集热点
        </button>
        <button class="btn btn-primary" @click="quickScript" :disabled="loading || !topics.length">
          ✍️ 生成文案
        </button>
        <button class="btn btn-primary" @click="quickImages" :disabled="loading || !scripts.length">
          🖼️ 生成图片
        </button>
      </div>
    </div>

    <div class="card" v-if="topics.length">
      <h3>🔥 最新热点 ({{ topics.length }})</h3>
      <table>
        <thead><tr><th>话题</th><th>来源</th><th>热度</th></tr></thead>
        <tbody>
          <tr v-for="t in topics.slice(0, 5)" :key="t.title">
            <td>{{ t.title }}</td>
            <td><span class="tag">{{ t.source }}</span></td>
            <td>{{ formatHot(t.hot_score) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" v-if="msg">
      <h3>📝 消息</h3>
      <pre class="msg-box">{{ msg }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const status = ref({ status: 'idle', step: null })
const topics = ref([])
const scripts = ref([])
const imageDirs = ref([])
const loading = ref(false)
const msg = ref('')

const statusText = computed(() => {
  const map = { idle: '空闲', running: '运行中', error: '错误' }
  return map[status.value.status] || status.value.status
})

function formatHot(n) {
  if (!n) return '-'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toString()
}

async function loadData() {
  try {
    const [s, sc, img] = await Promise.all([
      api.getStatus().catch(() => ({ status: 'idle' })),
      api.listScripts().catch(() => ({ scripts: [] })),
      api.listImages().catch(() => ({ image_dirs: [] })),
    ])
    status.value = s
    scripts.value = sc.scripts || []
    imageDirs.value = img.image_dirs || []
  } catch (e) {
    msg.value = `加载失败: ${e.message}`
  }
}

async function quickScrape() {
  loading.value = true; msg.value = '采集中...'
  try {
    const res = await api.scrapeTopics()
    topics.value = res.topics || []
    msg.value = `采集到 ${res.count} 条话题`
  } catch (e) { msg.value = `采集失败: ${e.message}` }
  finally { loading.value = false }
}

async function quickScript() {
  if (!topics.value.length) return
  loading.value = true; msg.value = '生成文案...'
  try {
    const t = topics.value[0]
    const res = await api.generateScript({ topic: t.title, persona: '知识科普博主', scene_count: 5 })
    msg.value = `文案已生成: ${res.path}\n${JSON.stringify(res.script?.scenes?.length || 0)} 个分镜`
    loadData()
  } catch (e) { msg.value = `生成失败: ${e.message}` }
  finally { loading.value = false }
}

async function quickImages() {
  loading.value = true; msg.value = '生成图片...'
  try {
    const res = await api.generateImages()
    msg.value = `已生成 ${res.count} 张图片`
    loadData()
  } catch (e) { msg.value = `生成失败: ${e.message}` }
  finally { loading.value = false }
}

onMounted(loadData)
</script>

<style scoped>
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: #888; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; }
.actions { display: flex; gap: 12px; }
.msg-box { background: #f5f5f5; padding: 12px; border-radius: 6px; font-size: 13px; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }
</style>