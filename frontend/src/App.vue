<template>
  <div class="app-container">
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <div class="logo">
            <span class="logo-text">WriterClaw</span>
          </div>
          <el-menu
            mode="horizontal"
            :default-active="activeMenu"
            class="header-menu"
            :ellipsis="false"
            @select="handleMenuSelect"
          >
            <el-menu-item index="home">灵感列表</el-menu-item>
            <el-menu-item index="create">新建灵感</el-menu-item>
          </el-menu>
        </div>
        <div class="header-right">
          <el-button text class="theme-toggle-btn" @click="toggleTheme">
            <el-icon>
              <component :is="isDark ? Sunny : Moon" />
            </el-icon>
            <span>{{ isDark ? '日间' : '暗夜' }}</span>
          </el-button>
          <el-button text @click="openApiConfig">
            <el-icon><Setting /></el-icon>
            <span>API</span>
          </el-button>
          <el-button text>
            <el-icon><User /></el-icon>
          </el-button>
        </div>
      </el-header>

      <!-- API 配置对话框 - 放在 header 外面 -->
      <el-dialog
        v-model="apiConfigVisible"
        title="API 配置"
        width="400px"
      >
        <el-form :model="apiConfig" label-width="100px">
          <el-form-item label="MiniMax API Key">
            <el-input
              v-model="apiConfig.minimaxKey"
              type="password"
              placeholder="请输入 MiniMax API Key"
              show-password
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="apiConfigVisible = false">取消</el-button>
            <el-button type="primary" @click="saveApiConfig">保存</el-button>
          </span>
        </template>
      </el-dialog>
      <el-container>
        <el-aside width="240px" class="sidebar" v-if="showSidebar">
          <div class="sidebar-header">
            <el-button type="primary" @click="goToCreate" class="new-btn">
              <el-icon><Plus /></el-icon>
              新建灵感
            </el-button>
          </div>
          <el-scrollbar>
            <div class="paper-list">
              <div
                v-for="paper in papers"
                :key="paper.id"
                class="paper-item"
                :class="{ active: currentPaperId === paper.id }"
                @click="selectPaper(paper.id)"
              >
                <el-icon><Document /></el-icon>
                <span class="paper-title">{{ paper.title }}</span>
                <el-tag :type="getStatusType(paper.status)" size="small">
                  {{ getStatusText(paper.status) }}
                </el-tag>
              </div>
            </div>
          </el-scrollbar>
        </el-aside>
        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <transition name="page" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePaperStore } from '@/stores/paper'
import { Document, Plus, User, Moon, Sunny, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const paperStore = usePaperStore()

const papers = computed(() => paperStore.papers)
const currentPaperId = computed(() => paperStore.currentPaper?.id)
const showSidebar = computed(() => route.name !== 'home')
const activeMenu = computed(() => route.name === 'home' ? 'home' : 'create')
const isDark = ref(false)
const apiConfigVisible = ref(false)
const apiConfig = ref({
  minimaxKey: ''
})

const applyTheme = (dark) => {
  isDark.value = dark
  document.documentElement.classList.toggle('theme-dark', dark)
  localStorage.setItem('theme-mode', dark ? 'dark' : 'light')
}

onMounted(() => {
  paperStore.fetchPapers()

  const savedTheme = localStorage.getItem('theme-mode')
  if (savedTheme === 'dark') {
    applyTheme(true)
  } else if (savedTheme === 'light') {
    applyTheme(false)
  } else {
    const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
    applyTheme(!!prefersDark)
  }
})

const goToCreate = () => {
  router.push('/create')
}

const selectPaper = (id) => {
  router.push(`/paper/${id}`)
}

const handleMenuSelect = (index) => {
  if (index === 'home') {
    router.push('/')
    return
  }
  if (index === 'create') {
    router.push('/create')
  }
}

const toggleTheme = () => {
  applyTheme(!isDark.value)
}

const openApiConfig = () => {
  // 从本地存储加载保存的 API key
  const savedKey = localStorage.getItem('minimaxApiKey')
  if (savedKey) {
    apiConfig.value.minimaxKey = savedKey
  }
  apiConfigVisible.value = true
}

const saveApiConfig = () => {
  // 保存 API key 到本地存储
  localStorage.setItem('minimaxApiKey', apiConfig.value.minimaxKey)
  apiConfigVisible.value = false
  ElMessage.success('API 配置已保存')
}

const getStatusType = (status) => {
  const types = {
    draft: 'info',
    outline_generated: 'warning',
    generating: 'primary',
    completed: 'success'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    draft: '草稿',
    outline_generated: '大纲已生成',
    generating: '生成中',
    completed: '已完成'
  }
  return texts[status] || '未知'
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --primary-color: #3A5FD9;
  --primary-light: #EEF2FF;
  --primary-dark: #2C4FBE;
  --success-color: #0FA47A;
  --warning-color: #D89A34;
  --danger-color: #EF4444;
  --text-primary: #0F172A;
  --text-secondary: #475569;
  --text-muted: #94A3B8;
  --bg-primary: #F3F6FC;
  --bg-secondary: #FFFFFF;
  --bg-tertiary: #E8EEF9;
  --border-color: #DDE6F4;
  --border-light: #EAF0FA;
  --shadow-sm: 0 4px 14px rgba(14, 30, 84, 0.06);
  --shadow-md: 0 10px 28px rgba(15, 32, 77, 0.12);
  --shadow-lg: 0 16px 40px rgba(12, 28, 70, 0.18);
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --app-bg: radial-gradient(circle at 20% 0%, #eef2ff 0%, #f4f7fd 45%, #edf2fb 100%);
}

:root.theme-dark {
  --primary-color: #7d9bff;
  --primary-light: #1b2650;
  --primary-dark: #93adff;
  --success-color: #2ecf9d;
  --warning-color: #f3bb58;
  --danger-color: #ff7b7b;
  --text-primary: #e2e8f0;
  --text-secondary: #a3b4d0;
  --text-muted: #7d8da8;
  --bg-primary: #0b1226;
  --bg-secondary: #121c35;
  --bg-tertiary: #172442;
  --border-color: #24365f;
  --border-light: #203055;
  --shadow-sm: 0 8px 20px rgba(1, 6, 18, 0.45);
  --shadow-md: 0 12px 32px rgba(0, 4, 14, 0.58);
  --shadow-lg: 0 20px 44px rgba(0, 3, 12, 0.68);
  --app-bg: radial-gradient(circle at 20% 0%, #101a36 0%, #0c1530 42%, #091126 100%);
}

html,
body {
  height: 100%;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  background: var(--app-bg);
  color: var(--text-primary);
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
}

.app-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.app-container > .el-container {
  height: 100%;
}

.app-container > .el-container > .el-container {
  min-height: 0;
}

.el-header.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  padding: 0 32px;
  height: 64px;
  box-shadow: var(--shadow-sm);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 40px;
}

.logo {
  display: flex;
  align-items: center;
}

.logo-text {
  font-size: 24px;
  font-weight: 800;
  background: linear-gradient(135deg, #3a5fd9 0%, #4f74f0 55%, #7f9cff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 1px;
  position: relative;
}

.logo-text::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, #3a5fd9, #4f74f0, #7f9cff);
  border-radius: 2px;
}

.header-menu {
  border-bottom: none;
  background: transparent;
}

.header-menu .el-menu-item {
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.header-menu .el-menu-item:hover {
  color: var(--primary-color);
  background: var(--primary-light);
}

.header-menu .el-menu-item.is-active {
  color: var(--primary-color);
  background: var(--primary-light);
  border-bottom: 2px solid var(--primary-color);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.theme-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sidebar {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: var(--shadow-sm);
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.new-btn {
  width: 100%;
  height: 44px;
  font-weight: 500;
  background: linear-gradient(135deg, var(--primary-color) 0%, #60A5FA 100%);
  border: none;
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
}

.new-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.paper-list {
  padding: 12px;
}

.paper-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  border: 1px solid transparent;
}

.paper-item:hover {
  background: var(--bg-tertiary);
  border-color: rgba(37, 99, 235, 0.1);
}

.paper-item.active {
  background: var(--primary-light);
  border-color: rgba(37, 99, 235, 0.2);
  color: var(--primary-color);
}

.paper-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
}

.main-content {
  background: var(--bg-primary);
  padding: 24px;
  height: calc(100vh - 64px);
  min-height: 0;
  overflow: hidden;
}

.el-main {
  padding: 24px !important;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.theme-dark .el-header.header,
.theme-dark .sidebar {
  background: rgba(18, 28, 53, 0.9);
  border-color: rgba(36, 54, 95, 0.7);
}

.theme-dark .paper-item:hover {
  background: rgba(126, 155, 255, 0.12);
}

.theme-dark .paper-item.active {
  background: rgba(126, 155, 255, 0.18);
  border-color: rgba(126, 155, 255, 0.32);
}

.theme-dark .header-menu .el-menu-item {
  color: var(--text-secondary);
}

.theme-dark .header-menu .el-menu-item:hover,
.theme-dark .header-menu .el-menu-item.is-active {
  color: var(--text-primary);
  background: rgba(126, 155, 255, 0.14);
}

.theme-dark .el-input__wrapper,
.theme-dark .el-textarea__inner,
.theme-dark .el-select__wrapper,
.theme-dark .el-card,
.theme-dark .step-content,
.theme-dark .steps-container,
.theme-dark .paper-viewer,
.theme-dark .paper-section,
.theme-dark .chapter-item,
.theme-dark .page-header,
.theme-dark .paper-card {
  background-color: #121c35 !important;
  border-color: var(--border-light) !important;
  color: var(--text-primary) !important;
}

.theme-dark .home-page,
.theme-dark .create-page,
.theme-dark .paper-detail,
.theme-dark .page-title,
.theme-dark .card-title,
.theme-dark .paper-title,
.theme-dark .chapter-title,
.theme-dark .section-title,
.theme-dark .sidebar-section h4,
.theme-dark .outline-section h4,
.theme-dark .info-item .value,
.theme-dark .chapter-text,
.theme-dark .section-text,
.theme-dark .content-text,
.theme-dark .streaming-content {
  color: var(--text-primary) !important;
}

.theme-dark .page-subtitle,
.theme-dark .card-meta,
.theme-dark .status-text,
.theme-dark .word-count,
.theme-dark .info-item .label,
.theme-dark .section-number,
.theme-dark .hint,
.theme-dark .empty-description,
.theme-dark .empty-placeholder,
.theme-dark .empty-placeholder p,
.theme-dark .section-pending p {
  color: var(--text-secondary) !important;
}

.theme-dark .page-header,
.theme-dark .steps-container,
.theme-dark .step-content,
.theme-dark .paper-viewer,
.theme-dark .paper-card,
.theme-dark .chapter-item,
.theme-dark .paper-section,
.theme-dark .viewer-content,
.theme-dark .viewer-sidebar,
.theme-dark .outline-tree,
.theme-dark .empty-state {
  background: #121c35 !important;
  border-color: var(--border-light) !important;
}

.theme-dark .nav-chapter-title:hover,
.theme-dark .nav-section:hover {
  background: rgba(125, 155, 255, 0.16) !important;
}

.theme-dark .nav-chapter-title.active,
.theme-dark .nav-section.active {
  background: rgba(125, 155, 255, 0.22) !important;
  color: #dbe5ff !important;
}

.theme-dark .section-pending,
.theme-dark .section-empty,
.theme-dark .section-loading-box {
  background: #162445 !important;
  border-color: #2a3f6d !important;
}

.theme-dark .pending-lines .line,
.theme-dark .skeleton-line {
  background: linear-gradient(90deg, #24365c 15%, #2d4270 50%, #24365c 85%) !important;
  background-size: 220% 100% !important;
}

.theme-dark .el-dialog,
.theme-dark .el-dialog__body,
.theme-dark .el-dialog__header,
.theme-dark .el-dialog__footer {
  background: #121c35 !important;
  color: var(--text-primary) !important;
}

.theme-dark .el-empty__description p {
  color: var(--text-secondary) !important;
}

.el-card {
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.el-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.el-button {
  border-radius: var(--radius-md);
  font-weight: 500;
  transition: all 0.2s ease;
}

.el-button--primary {
  background: linear-gradient(135deg, var(--primary-color) 0%, #60A5FA 100%);
  border: none;
}

.el-button--primary:hover {
  background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.el-button--warning {
  background: linear-gradient(135deg, var(--warning-color) 0%, #FBBF24 100%);
  border: none;
}

.el-button--warning:hover {
  background: linear-gradient(135deg, #D97706 0%, var(--warning-color) 100%);
  transform: translateY(-1px);
}

.el-input__wrapper {
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--border-color) inset;
  transition: all 0.2s ease;
}

.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #CBD5E1 inset;
}

.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2), 0 0 0 1px var(--primary-color) inset;
}

.el-tag {
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.el-dialog {
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.el-dialog__header {
  border-bottom: 1px solid var(--border-light);
  padding: 20px 24px;
}

.el-dialog__title {
  font-weight: 600;
  font-size: 18px;
}

.el-form-item__label {
  font-weight: 500;
  color: var(--text-secondary);
}

.el-breadcrumb__item {
  font-size: 14px;
}

.el-breadcrumb__inner {
  color: var(--text-muted);
}

.el-breadcrumb__inner.is-link:hover {
  color: var(--primary-color);
}

.el-breadcrumb__item:last-child .el-breadcrumb__inner {
  color: var(--text-primary);
  font-weight: 500;
}

.el-message {
  border-radius: var(--radius-md);
}

.el-select .el-input__wrapper {
  border-radius: var(--radius-md);
}

.el-textarea__inner {
  border-radius: var(--radius-md);
}

.el-textarea__inner:focus {
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2), 0 0 0 1px var(--primary-color) inset;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #CBD5E1 0%, #94A3B8 100%);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #94A3B8 0%, #64748B 100%);
}

.el-scrollbar__bar {
  opacity: 0;
  transition: opacity 0.3s;
}

.el-scrollbar:hover .el-scrollbar__bar {
  opacity: 1;
}

.el-tree {
  background: transparent;
}

.el-tree-node__content {
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
}

.el-tree-node__content:hover {
  background: var(--bg-tertiary);
}

.el-tree-node.is-current > .el-tree-node__content {
  background: var(--primary-light);
  color: var(--primary-color);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.scale-enter-active,
.scale-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.slide-left-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.page-enter-active,
.page-leave-active {
  transition: all 0.4s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

@keyframes float-gentle {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes ripple {
  0% {
    transform: scale(0);
    opacity: 1;
  }
  100% {
    transform: scale(4);
    opacity: 0;
  }
}

.btn-ripple {
  position: relative;
  overflow: hidden;
}

.btn-ripple::after {
  content: '';
  position: absolute;
  width: 100px;
  height: 100px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  transform: scale(0);
  pointer-events: none;
}

.btn-ripple:active::after {
  animation: ripple 0.6s ease-out;
}

.hover-lift {
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
}

.hover-glow {
  transition: all 0.3s ease;
}

.hover-glow:hover {
  box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
}

.gradient-border {
  position: relative;
}

.gradient-border::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(135deg, #667eea, #764ba2, #f093fb);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.gradient-border:hover::before {
  opacity: 1;
}

.stagger-enter-active {
  transition: all 0.5s ease;
}

.stagger-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.stagger-leave-active {
  transition: all 0.3s ease;
}

.stagger-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
