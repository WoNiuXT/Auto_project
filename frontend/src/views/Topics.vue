<template>
  <div class="page">
    <h1>🔥 热点采集</h1>
    <p class="subtitle">从 DailyHotApi 获取全网热搜</p>

    <div class="card">
      <div class="toolbar">
        <button class="btn btn-primary" @click="scrape" :disabled="loading">
          {{ loading ? '采集中...' : '🔥 采集热搜' }}
        </button>
        <div class="toolbar-right">
          <span class="tag">已采集 {{ topics.length }} 条</span>
        </div>
      </div>
    </div>

    <div class="empty" v-if="!topics.length && !loading">暂无数据，点击"采集热搜"开始</div>
    <div class="loading" v-if="loading">正在采集，请稍候...</div>

    <div class="card" v-if="topics.length">
      <table>
        <thead>
          <tr><th>#</th><th>话题</th><th>来源</th><th>热度</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="(t, i) in topics" :key="i">
            <td>{{ i + 1 }}</td>
            <td>{{ t.title }}</td>
            <td><span class="tag">{{ t.source }}</span></td>
            <td>{{ formatHot(t.hot_score) }}</td>
            <td>
              <button class="btn btn-secondary" @click="goScript(t)" style="padding:4px 12px;font-size:12px">
                生成文案
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const topics = ref([])
const loading = ref(false)

function formatHot(n) {
  if (!n) return '-'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toString()
}

async function scrape() {
  loading.value = true
  try {
    const res = await api.scrapeTopics()
    topics.value = res.topics || []
  } catch (e) { alert('采集失败: ' + e.message) }
  finally { loading.value = false }
}

function goScript(topic) {
  router.push({ path: '/scripts', query: { topic: topic.title } })
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.toolbar-right { display: flex; gap: 8px; align-items: center; }
</style>