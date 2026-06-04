import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/topics', name: 'Topics', component: () => import('../views/Topics.vue') },
  { path: '/scripts', name: 'Scripts', component: () => import('../views/Scripts.vue') },
  { path: '/images', name: 'Images', component: () => import('../views/Images.vue') },
  { path: '/publish', name: 'Publish', component: () => import('../views/Publish.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router