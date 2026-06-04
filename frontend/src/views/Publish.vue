<template>
  <div class="page">
    <h1>🚀 发布管理</h1>
    <p class="subtitle">多平台发布 + Cookie 管理</p>

    <!-- Cookie 状态 -->
    <div class="card">
      <h3>🔑 Cookie 状态</h3>
      <div class="cookie-grid">
        <div class="cookie-item" v-for="(info, platform) in cookies" :key="platform">
          <span class="platform-name">{{ platformNames[platform] || platform }}</span>
          <span class="status" :class="info.valid ? 'status-idle' : 'status-error'">
            {{ info.valid ? '有效' : '失效' }}
          </span>
          <span class="cookie-msg">{{ info.message }}</span>
        </div>
      </div>
      <button class="btn btn-secondary" @click="checkCookies" style="margin-top:12px">🔄 刷新状态</button>
    </div>

    <!-- 发布表单 -->
    <div class="card">
      <h3>📝 发布内容</h3>
      <div class="form-row">
        <label>平台：</label>
        <div class="platform-select">
          <label v-for="p in allPlatforms" :key="p.key">
            <input type="checkbox" v-model="selectedPlatforms" :value="p.key" />
            {{ p.name }}
          </label>
        </div>
      </div>
      <div class="form-row">
        <label>文案：</label>
        <textarea v-model="caption" placeholder="输入发布文案..." rows="3" style="flex:1"></textarea>
      </div>
      <button class="btn btn-primary" @click="publish" :disabled="loading || !selectedPlatforms.length">
        {{ loading ? '发布中...' : '🚀 开始发布' }}
      </button>
    </div>

    <!-- 发布结果 -->
    <div class="card" v-if="results.length">
      <h3>📋 发布结果</h3>
      <table>
        <thead><tr><th>平台</th><th>状态</th><th>链接</th><th>错误</th></tr></thead>
        <tbody>
          <tr v-for="r in results" :key="r.platform">
            <td>{{ platformNames[r.platform] || r.platform }}</td>
            <td>
              <span class="status" :class="r.status === 'success' ? 'status-idle' : 'status-error'">
                {{ r.status }}
              </span>
            </td>
            <td><a v-if="r.publish_url" :href="r.publish_url" target="_blank">查看</a><span v-else>-</span></td>
            <td>{{ r.error || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const platformNames = { douyin: '抖音', bilibili: 'B站', xhs: '小红书' }
const allPlatforms = [
  { key: 'douyin', name: '抖音' },
  { key: 'bilibili', name: 'B站' },
  { key: 'xhs', name: '小红书' },
]

const cookies = ref({})
const selectedPlatforms = ref(['douyin'])
const caption = ref('')
const loading = ref(false)
const results = ref([])

async function checkCookies() {
  try { cookies.value = await api.checkCookies() }
  catch (e) { alert('检查失败: ' + e.message) }
}

async function publish() {
  loading.value = true
  try {
    const res = await api.publish({
      platforms: selectedPlatforms.value,
      caption: caption.value,
      image_paths: [],
    })
    results.value = res.results || []
  } catch (e) { alert('发布失败: ' + e.message) }
  finally { loading.value = false }
}

onMounted(checkCookies)
</script>

<style scoped>
.cookie-grid { display: flex; gap: 20px; flex-wrap: wrap; }
.cookie-item { display: flex; align-items: center; gap: 8px; }
.platform-name { font-weight: 600; min-width: 50px; }
.cookie-msg { color: #888; font-size: 12px; }
.form-row { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }
.form-row label { font-size: 14px; white-space: nowrap; min-width: 50px; padding-top: 8px; }
.platform-select { display: flex; gap: 16px; padding-top: 6px; }
.platform-select label { display: flex; align-items: center; gap: 4px; font-size: 14px; cursor: pointer; }
</style>