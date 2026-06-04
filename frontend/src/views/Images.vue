<template>
  <div class="page">
    <h1>🖼️ 图片管理</h1>
    <p class="subtitle">ComfyUI 多版本生图 + 审核选用</p>

    <div class="card">
      <div class="toolbar">
        <button class="btn btn-primary" @click="generate" :disabled="loading">
          {{ loading ? '生成中..' : '🖼️ 生成图片' }}
        </button>
        <span class="tag">已生成 {{ imageDirs.length }} 组</span>
        <span class="tag" v-if="selectedCount > 0" style="color:#4caf50">已选用 {{ selectedCount }} 张</span>
      </div>
    </div>

    <div class="loading" v-if="loading">ComfyUI 生图中，每个场景生成多个变体，请稍候..</div>

    <!-- 图片组 -->
    <div class="card" v-for="group in imageDirs" :key="group.dir">
      <h3>🖼️ {{ group.dir }} ({{ group.count }} 张)</h3>
      <div class="image-grid">
        <div class="image-item" v-for="img in group.images" :key="img.path"
             :class="{ 'image-selected': isSceneSelected(img.scene_id, img.variant) }">
          <div class="image-box">
            <img v-if="img.path" :src="'/api/file?path=' + encodeURIComponent(img.path)" 
                 :alt="'Scene ' + img.scene_id + ' V' + img.variant"
                 @error="img._err = true" />
            <div v-if="!img.path || img._err" class="image-placeholder">
              <span>Scene {{ img.scene_id }} / V{{ img.variant }}</span>
            </div>
            <div v-if="isSceneSelected(img.scene_id, img.variant)" class="selected-badge">✓ 已选用</div>
          </div>
          <div class="image-info">
            <span class="tag">seed: {{ img.seed }}</span>
            <button class="btn btn-secondary" style="padding:2px 8px;font-size:11px;margin-left:4px"
              :class="{ 'btn-selected': isSceneSelected(img.scene_id, img.variant) }"
              @click="selectImage(img)">
              {{ isSceneSelected(img.scene_id, img.variant) ? '✓ 已选用' : '✅ 选用' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="empty" v-if="!imageDirs.length && !loading">
      暂无图片，请先在"文案管理"生成分镜脚本后再生成图片
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const imageDirs = ref([])
const loading = ref(false)
// 存储每个 scene_id 当前选中的 variant: { scene_id: variant }
const selectedMap = ref({})

const selectedCount = computed(() => Object.keys(selectedMap.value).length)

function isSceneSelected(sceneId, variant) {
  return selectedMap.value[sceneId] === variant
}

async function loadImages() {
  try {
    const res = await api.listImages()
    imageDirs.value = res.image_dirs || []
  } catch (e) { /* ignore */ }
}

async function generate() {
  loading.value = true
  try {
    await api.generateImages()
    await loadImages()
  } catch (e) { alert('生成失败: ' + e.message) }
  finally { loading.value = false }
}

async function selectImage(img) {
  try {
    const res = await api.selectImage({
      scene_id: img.scene_id,
      selected_variant: img.variant
    })
    // 更新本地选中状态
    selectedMap.value[img.scene_id] = img.variant
    // 强制触发响应式
    selectedMap.value = { ...selectedMap.value }
  } catch (e) {
    alert('选用失败: ' + e.message)
  }
}

onMounted(loadImages)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.image-item { border: 2px solid #eee; border-radius: 6px; overflow: hidden; transition: border-color 0.2s; }
.image-item.image-selected { border-color: #4caf50; }
.image-box { position: relative; }
.image-box img { width: 100%; height: auto; display: block; }
.image-placeholder {
  height: 160px; background: #e3f2fd; display: flex; align-items: center;
  justify-content: center; font-size: 13px; color: #666;
}
.selected-badge {
  position: absolute; top: 8px; right: 8px;
  background: #4caf50; color: white; padding: 2px 8px;
  border-radius: 4px; font-size: 12px; font-weight: 600;
}
.image-info { padding: 8px; display: flex; align-items: center; justify-content: space-between; }
.btn-selected { background: #4caf50 !important; color: white !important; }
</style>