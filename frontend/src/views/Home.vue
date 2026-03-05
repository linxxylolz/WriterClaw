<template>
  <div class="home-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">灵感中心</h1>
        <p class="page-subtitle">开始您的创意写作之旅</p>
      </div>
      <el-button type="primary" size="large" @click="goToCreate" class="create-btn">
        <el-icon><Plus /></el-icon>
        新建灵感
      </el-button>
    </div>

    <transition-group name="card-list" tag="div" class="paper-grid" v-if="papers.length > 0">
      <div
        v-for="(paper, index) in papers"
        :key="paper.id"
        class="paper-card"
        :style="{ animationDelay: `${index * 0.05}s` }"
        @click="openPaper(paper.id)"
      >
        <div class="card-bg-decoration"></div>
        <div class="card-header">
          <el-tag :type="getTypeTag(paper.paper_type)" size="small" effect="dark">
            {{ getTypeText(paper.paper_type) }}
          </el-tag>
          <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, paper)">
            <el-button text size="small" class="more-btn" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="delete">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <h3 class="card-title">{{ paper.title }}</h3>
        <div class="card-meta">
          <span>
            <el-icon><Document /></el-icon>
            {{ paper.generated_word_count || 0 }} / {{ paper.target_word_count || paper.word_count || 0 }} 字
          </span>
          <span>
            <el-icon><Clock /></el-icon>
            {{ formatDate(paper.created_at) }}
          </span>
        </div>
        <div class="card-footer">
          <el-progress
            :percentage="getProgress(paper)"
            :stroke-width="6"
            :show-text="false"
            :color="getProgressColor(paper.status)"
          />
          <span class="status-text">{{ getStatusText(paper.status) }}</span>
        </div>
      </div>
    </transition-group>

    <div v-else class="empty-state">
      <div class="empty-illustration">
        <el-icon :size="80" color="#E2E8F0"><Document /></el-icon>
      </div>
      <h3 class="empty-title">暂无灵感</h3>
      <p class="empty-description">点击下方按钮开始创建您的第一个灵感</p>
      <el-button type="primary" size="large" @click="goToCreate" class="create-btn">
        <el-icon><Plus /></el-icon>
        新建文稿
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePaperStore } from '@/stores/paper'
import { Plus, MoreFilled, Document, Clock } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'

const router = useRouter()
const paperStore = usePaperStore()

const papers = computed(() => paperStore.papers)

const goToCreate = () => {
  router.push('/create')
}

const openPaper = (id) => {
  router.push(`/paper/${id}`)
}

const getTypeTag = (type) => {
  const types = {
    graduation: 'success',
    course: 'warning',
    proposal: 'info',
    review: 'primary'
  }
  return types[type] || 'info'
}

const getTypeText = (type) => {
  const texts = {
    graduation: '毕业报告',
    course: '课程报告',
    proposal: '开题报告',
    review: '文献综述'
  }
  return texts[type] || '文稿'
}

const getProgress = (paper) => {
  if (paper.status === 'completed') return 100
  if (paper.status === 'generating') return 60
  if (paper.status === 'outline_generated') return 30
  return 10
}

const getProgressColor = (status) => {
  const colors = {
    draft: '#94A3B8',
    outline_generated: '#F59E0B',
    generating: '#2563EB',
    completed: '#10B981'
  }
  return colors[status] || '#94A3B8'
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

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}-${date.getDate()}`
}

const handleCommand = (command, paper) => {
  if (command === 'delete') {
    ElMessageBox.confirm('确定要删除这条灵感吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(async () => {
      await paperStore.deletePaper(paper.id)
      ElMessage.success('删除成功')
    }).catch(() => {})
  }
}
</script>

<style scoped>
.home-page {
  height: 100%;
  min-height: 0;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(58, 95, 217, 0.1) 0%, rgba(130, 156, 255, 0.12) 100%);
  border-radius: 16px;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #3a5fd9 0%, #6e8eff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 14px;
  color: #94A3B8;
}

.create-btn {
  height: 48px;
  padding: 0 28px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #3a5fd9 0%, #5d7ef2 100%);
  border: none;
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.create-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.paper-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  overflow: auto;
  min-height: 0;
  padding-right: 4px;
}

.paper-card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  border: 1px solid var(--border-light);
  position: relative;
  overflow: hidden;
  animation: cardSlideIn 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

@keyframes cardSlideIn {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.paper-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3a5fd9, #6e8eff);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.paper-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-md);
  border-color: rgba(58, 95, 217, 0.28);
}

.paper-card:hover::before {
  opacity: 1;
}

.paper-card:active {
  transform: translateY(-2px);
}

.card-bg-decoration {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(102, 126, 234, 0.05) 0%, transparent 70%);
  pointer-events: none;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.more-btn {
  color: #94A3B8;
  transition: color 0.2s ease;
}

.more-btn:hover {
  color: #667eea;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  gap: 20px;
  color: #64748B;
  font-size: 14px;
  margin-bottom: 20px;
}

.card-meta span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-footer .el-progress {
  flex: 1;
}

.status-text {
  font-size: 13px;
  color: #94A3B8;
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-illustration {
  margin-bottom: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.empty-title {
  font-size: 24px;
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 8px;
}

.empty-description {
  font-size: 16px;
  color: #94A3B8;
  margin-bottom: 32px;
}

.card-list-enter-active {
  transition: all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.card-list-leave-active {
  transition: all 0.3s ease;
}

.card-list-enter-from {
  opacity: 0;
  transform: scale(0.9) translateY(20px);
}

.card-list-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(-20px);
}

.card-list-move {
  transition: transform 0.5s ease;
}

@media (max-width: 768px) {
  .home-page {
    padding: 0 16px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 20px;
    text-align: center;
  }
  
  .paper-grid {
    grid-template-columns: 1fr;
  }
}
</style>
