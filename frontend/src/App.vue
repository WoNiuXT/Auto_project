<template>
  <div id="app">
    <nav class="sidebar">
      <div class="logo">🔄 Auto_pipeline</div>
      <router-link to="/" class="nav-item" exact-active-class="active">📊 仪表盘</router-link>
      <router-link to="/topics" class="nav-item" active-class="active">🔥 热点采集</router-link>
      <router-link to="/scripts" class="nav-item" active-class="active">✍️ 文案管理</router-link>
      <router-link to="/images" class="nav-item" active-class="active">🖼️ 图片管理</router-link>
      <router-link to="/publish" class="nav-item" active-class="active">🚀 发布管理</router-link>
    </nav>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
#app {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  width: 220px;
  background: #1a1a2e;
  color: #eee;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}
.logo {
  font-size: 18px;
  font-weight: 700;
  padding: 12px 20px 24px;
  border-bottom: 1px solid #333;
  margin-bottom: 12px;
}
.nav-item {
  display: block;
  padding: 10px 20px;
  color: #aaa;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}
.nav-item:hover { color: #fff; background: #2a2a4a; }
.nav-item.active { color: #4fc3f7; background: #16213e; border-left: 3px solid #4fc3f7; }
.content {
  flex: 1;
  padding: 24px 32px;
  background: #f5f7fa;
  overflow-y: auto;
}
</style>