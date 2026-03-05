import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import CreatePaper from '@/views/CreatePaper.vue'
import PaperDetail from '@/views/PaperDetail.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home
  },
  {
    path: '/create',
    name: 'create',
    component: CreatePaper
  },
  {
    path: '/paper/:id',
    name: 'paper',
    component: PaperDetail
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
