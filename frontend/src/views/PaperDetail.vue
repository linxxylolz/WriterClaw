<template>
  <div class="paper-detail">
    <div class="detail-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">灵感列表</el-breadcrumb-item>
        <el-breadcrumb-item>{{ paper?.title || '灵感详情' }}</el-breadcrumb-item>
      </el-breadcrumb>
      <div class="header-actions">
        <el-button @click="goBack" :disabled="generatingAll">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <el-button 
          type="warning" 
          @click="generateAllSections" 
          :loading="generatingAll"
          :disabled="generatingAll || !!generatingSection || generatingOutline"
        >
          <el-icon><Grid /></el-icon>
          {{ generatingAll ? `生成中 ${generatingProgress.current}/${generatingProgress.total}` : '一键生成' }}
        </el-button>
        <el-button 
          type="primary" 
          @click="exportWord"
          :disabled="generatingAll || !!generatingSection || generatingOutline"
        >
          <el-icon><Download /></el-icon>
          导出Word
        </el-button>
      </div>
    </div>

    <div class="generating-status" v-if="generatingAll">
      <div class="status-progress">
        <el-progress 
          :percentage="Math.round((generatingProgress.current / generatingProgress.total) * 100)" 
          :stroke-width="8"
          :format="formatProgress"
        />
      </div>
      <div class="status-info">
        <span class="current-section">正在生成: {{ generatingSectionName }}</span>
      </div>
    </div>

    <div class="paper-viewer" v-if="paper">
      <div class="viewer-sidebar">
        <div class="sidebar-section">
          <h4>灵感信息</h4>
          <div class="info-item">
            <span class="label">标题:</span>
            <span class="value">{{ paper.title }}</span>
          </div>
          <div class="info-item">
            <span class="label">类型:</span>
            <el-tag size="small">{{ getTypeText(paper.paper_type) }}</el-tag>
          </div>
          <div class="info-item">
            <span class="label">字数:</span>
            <span class="value">{{ paper.generated_word_count || 0 }} / {{ paper.target_word_count || paper.word_count || 0 }} 字</span>
          </div>
          <div class="info-item">
            <span class="label">状态:</span>
            <el-tag :type="getStatusType(paper.status)" size="small">
              {{ getStatusText(paper.status) }}
            </el-tag>
          </div>
        </div>

        <el-divider />

        <div class="outline-section">
          <h4>目录导航</h4>
          <el-scrollbar>
            <div class="outline-nav">
              <div
                v-for="(chapter, chIndex) in paper.outline"
                :key="chapter.id"
                class="nav-chapter"
              >
                <div
                  class="nav-chapter-title"
                  :class="{ active: activeChapter === chIndex }"
                  @click="scrollToChapter(chIndex)"
                >
                  <span class="chapter-text">{{ chapter.title }}</span>
                </div>
                <div class="nav-sections">
                  <div
                    v-for="(section, secIndex) in chapter.sections"
                    :key="section.id"
                    class="nav-section"
                    :class="{ 
                      active: activeSection === `${chIndex}-${secIndex}`, 
                      filled: section.content && section.content.length > 50,
                      generating: generatingSection === section.id
                    }"
                    @click="scrollToSection(chIndex, secIndex)"
                  >
                    <el-icon v-if="section.content && section.content.length > 50" color="#10B981"><Check /></el-icon>
                    <el-icon v-else-if="generatingSection === section.id" class="section-loading"><Loading /></el-icon>
                    <el-icon v-else color="#CBD5E1"><Document /></el-icon>
                    <span class="section-text">{{ section.title }}</span>
                  </div>
                </div>
              </div>
            </div>
          </el-scrollbar>
        </div>
      </div>

      <div class="viewer-content">
        <el-scrollbar>
          <div class="paper-content" ref="paperContentRef">
            <div class="paper-header-section">
              <h1 class="paper-title">{{ paper.title }}</h1>
            </div>
            
            <div
              v-for="(chapter, chIndex) in paper.outline"
              :key="chapter.id"
              class="paper-chapter"
              :id="`chapter-${chIndex}`"
            >
              <h2 class="chapter-title">{{ chapter.title }}</h2>
              
              <div
                v-for="(section, secIndex) in chapter.sections"
                :key="section.id"
                class="paper-section"
                :id="`section-${chIndex}-${secIndex}`"
              >
                <div class="section-header">
                  <h3 class="section-title">{{ section.title }}</h3>
                  <div class="section-actions">
                    <el-button
                      size="small"
                      :type="section.content && section.content.length > 50 ? 'default' : 'primary'"
                      :loading="generatingSection === section.id"
                      :disabled="generatingAll || (!!generatingSection && generatingSection !== section.id) || generatingOutline"
                      @click="generateSection(chapter.id, section.id)"
                    >
                      {{ generatingSection === section.id ? '生成中...' : (section.content && section.content.length > 50 ? '重新生成' : '生成') }}
                    </el-button>
                    <el-button
                      size="small"
                      type="warning"
                      @click="openRefineDialog(chIndex, secIndex)"
                      :disabled="!section.content || generatingAll || !!generatingSection || generatingOutline"
                    >
                      微调
                    </el-button>
                    <el-button
                      size="small"
                      type="text"
                      @click="copySection(section.content)"
                      :disabled="!section.content"
                    >
                      复制
                    </el-button>
                  </div>
                </div>
                
                <div v-if="generatingSection === section.id && !streamingContent" class="section-loading-box">
                  <div class="loading-skeleton">
                    <div class="skeleton-line skeleton-title"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line short"></div>
                  </div>
                </div>
                
                <div v-else-if="generatingSection === section.id && streamingContent" class="section-streaming">
                  <div class="streaming-content">{{ streamingContent }}</div>
                  <div class="streaming-indicator">
                    <el-icon class="loading-icon"><Loading /></el-icon>
                    <span>实时生成中...</span>
                  </div>
                </div>
                
                <div v-else-if="!section.content || section.content.length < 50" class="section-empty">
                  <div class="empty-placeholder">
                    <el-icon :size="32" color="#CBD5E1"><Document /></el-icon>
                    <p>正在出稿请耐心等待</p>
                    <div class="pending-lines">
                      <span class="line title"></span>
                      <span class="line"></span>
                      <span class="line"></span>
                      <span class="line short"></span>
                    </div>
                  </div>
                </div>
                
                <div v-else class="section-content">
                  <div class="content-text">{{ section.content }}</div>
                  <div class="word-count">字数: {{ section.content.length }}</div>
                </div>
              </div>
            </div>

            <div v-if="!paper.outline || paper.outline.length === 0" class="empty-outline">
              <el-empty description="暂无大纲">
                <el-button type="primary" @click="generateOutline" :loading="generatingOutline" :disabled="generatingOutline || generatingAll">
                  {{ generatingOutline ? '生成中...' : '生成大纲' }}
                </el-button>
              </el-empty>
            </div>
          </div>
        </el-scrollbar>
      </div>
    </div>

    <el-empty v-else description="灵感不存在" />

    <el-dialog v-model="refineDialogVisible" title="段落微调" width="600px" :close-on-click-modal="false">
      <el-form>
        <el-form-item label="微调指令">
          <el-input
            v-model="refineInstruction"
            type="textarea"
            :rows="3"
            placeholder="请输入微调要求，如：'简化内容'、'增加案例'、'改写得更正式'、'扩展论述'"
            :disabled="refining"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="refineDialogVisible = false" :disabled="refining">取消</el-button>
        <el-button type="primary" @click="refineSection" :loading="refining">
          {{ refining ? '微调中...' : '确认微调' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePaperStore } from '@/stores/paper'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download, Check, Document, Grid, Loading } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const paperStore = usePaperStore()

const paper = computed(() => paperStore.currentPaper)
const generatingSection = ref(null)
const streamingContent = ref('')
const refining = ref(false)
const generatingAll = ref(false)
const generatingOutline = ref(false)
const generatingProgress = ref({ current: 0, total: 0 })

const activeChapter = ref(0)
const activeSection = ref('0-0')
const paperContentRef = ref(null)

const refineDialogVisible = ref(false)
const refineInstruction = ref('')
const refineTarget = ref({ chapterIndex: 0, sectionIndex: 0 })

const generatingSectionName = computed(() => {
  if (!generatingSection.value || !paper.value) return ''
  for (const chapter of paper.value.outline) {
    for (const section of chapter.sections) {
      if (section.id === generatingSection.value) {
        return `${chapter.title} - ${section.title}`
      }
    }
  }
  return ''
})

const formatProgress = (percentage) => {
  return `${percentage}%`
}

onMounted(async () => {
  const paperId = route.params.id
  if (paperId) {
    await paperStore.fetchPaper(paperId)
    if (route.query.autoGenerate === '1' && paperStore.currentPaper?.outline?.length) {
      await generateAllSections()
      router.replace({ path: `/paper/${paperId}` })
    }
  }
})

const goBack = () => {
  router.push('/')
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

const generateOutline = async () => {
  if (!paper.value) return
  try {
    generatingOutline.value = true
    const result = await paperStore.generateOutline(paper.value.id)
    if (result) {
      ElMessage.success('大纲生成成功')
    } else {
      ElMessage.error('大纲生成失败')
    }
  } finally {
    generatingOutline.value = false
  }
}

const generateSection = async (chapterId, sectionId) => {
  if (!paper.value) return
  try {
    generatingSection.value = sectionId
    streamingContent.value = ''
    
    await paperStore.generateSection(paper.value.id, chapterId, sectionId, (content) => {
      streamingContent.value = content
      const chapter = paper.value.outline.find(ch => ch.id === chapterId)
      if (chapter) {
        const section = chapter.sections.find(s => s.id === sectionId)
        if (section) {
          section.content = content
        }
      }
    })
    
    await paperStore.fetchPaper(paper.value.id)
  } finally {
    generatingSection.value = null
    streamingContent.value = ''
  }
}

const generateAllSections = async () => {
  if (!paper.value) return
  
  const apiKey = localStorage.getItem('minimaxApiKey')
  if (!apiKey || apiKey.trim() === '') {
    ElMessage.warning('请先配置 API Key，点击右上角"API"按钮进行配置')
    return
  }
  
  try {
    generatingAll.value = true
    generatingProgress.value = { current: 0, total: 0 }

    const pendingSections = []
    for (const chapter of paper.value.outline) {
      for (const section of chapter.sections) {
        if (!section.content || section.content.length < 120) {
          pendingSections.push({ chapter, section })
        }
      }
    }

    generatingProgress.value.total = pendingSections.length

    if (pendingSections.length === 0) {
      ElMessage.success('当前大纲内容已生成完成')
      return
    }

    for (const item of pendingSections) {
      generatingSection.value = item.section.id
      
      await paperStore.generateSection(paper.value.id, item.chapter.id, item.section.id, (content) => {
        item.section.content = content
      })
      generatingProgress.value.current++
    }
    
    await paperStore.fetchPaper(paper.value.id)
    ElMessage.success('全文生成完成！')
  } catch (error) {
    console.error('Generate all sections failed:', error)
    ElMessage.error('一键生成失败，请重试')
  } finally {
    generatingAll.value = false
    generatingSection.value = null
  }
}

const saveSection = async (chapterId, section) => {
  if (!paper.value) return
  await paperStore.updateSection(paper.value.id, chapterId, section.id, section)
}

const scrollToChapter = (index) => {
  activeChapter.value = index
  const element = document.getElementById(`chapter-${index}`)
  element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const scrollToSection = (chIndex, secIndex) => {
  activeChapter.value = chIndex
  activeSection.value = `${chIndex}-${secIndex}`
  const element = document.getElementById(`section-${chIndex}-${secIndex}`)
  element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const openRefineDialog = (chIndex, secIndex) => {
  refineTarget.value = { chapterIndex: chIndex, sectionIndex: secIndex }
  refineInstruction.value = ''
  refineDialogVisible.value = true
}

const refineSection = async () => {
  if (!paper.value || !refineInstruction.value) return
  const { chapterIndex, sectionIndex } = refineTarget.value
  const chapter = paper.value.outline[chapterIndex]
  const section = chapter.sections[sectionIndex]
  
  try {
    refining.value = true
    const result = await paperStore.refineSection(paper.value.id, chapter.id, section.id, refineInstruction.value)
    if (result) {
      refineDialogVisible.value = false
      ElMessage.success('段落微调完成')
    } else {
      ElMessage.error('段落微调失败')
    }
  } finally {
    refining.value = false
  }
}

const copySection = async (content) => {
  if (!content) return
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('复制成功')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const exportWord = async () => {
  if (!paper.value) return
  const result = await paperStore.exportPaper(paper.value.id)
  if (result?.success) {
    ElMessage.success('导出成功')
  } else {
    ElMessage.error('导出失败')
  }
}
</script>

<style scoped>
.paper-detail {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.generating-status {
  background: linear-gradient(135deg, #3a5fd9 0%, #5d7ef2 100%);
  padding: 16px 24px;
  border-radius: 12px;
  margin-bottom: 16px;
  color: white;
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.status-progress {
  margin-bottom: 8px;
}

.status-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.current-section {
  opacity: 0.9;
}

.paper-viewer {
  flex: 1;
  min-height: 0;
  display: flex;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
  background: #FFFFFF;
  box-shadow: var(--shadow-sm);
}

.viewer-sidebar {
  width: 300px;
  border-right: 1px solid var(--border-light);
  background: linear-gradient(180deg, #f8faff 0%, #f1f6ff 100%);
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

.sidebar-section {
  flex-shrink: 0;
}

.sidebar-section h4,
.outline-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1E293B;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.info-item .label {
  color: #64748B;
}

.info-item .value {
  color: #1E293B;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.outline-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.outline-section .el-scrollbar {
  flex: 1;
  overflow: hidden;
}

.outline-nav {
  padding-right: 8px;
}

.nav-chapter {
  margin-bottom: 4px;
}

.nav-chapter-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  color: #1E293B;
  background: transparent;
}

.nav-chapter-title:hover {
  background: rgba(58, 95, 217, 0.1);
}

.nav-chapter-title.active {
  background: linear-gradient(135deg, #3a5fd9 0%, #5d7ef2 100%);
  color: #FFFFFF;
  box-shadow: 0 6px 16px rgba(58, 95, 217, 0.24);
}

.nav-chapter-title.generating {
  background: rgba(216, 154, 52, 0.18);
  color: #d89a34;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.nav-sections {
  padding-left: 8px;
  margin-top: 4px;
}

.nav-section {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  font-size: 13px;
  color: #64748B;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.nav-section:hover {
  background: rgba(58, 95, 217, 0.08);
  color: #1E293B;
}

.nav-section.active {
  background: rgba(58, 95, 217, 0.12);
  color: #3a5fd9;
}

.nav-section.filled {
  color: #10B981;
}

.nav-section.generating {
  background: rgba(216, 154, 52, 0.12);
  color: #d89a34;
}

.section-loading {
  animation: spin 1s linear infinite;
}

.section-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.viewer-content {
  flex: 1;
  background: #FFFFFF;
  min-height: 0;
  overflow: hidden;
}

.viewer-content .el-scrollbar {
  height: 100%;
}

.paper-content {
  padding: 40px 48px;
  max-width: 900px;
  margin: 0 auto;
}

.paper-header-section {
  text-align: center;
  margin-bottom: 40px;
  padding-bottom: 24px;
  border-bottom: 2px solid var(--border-light);
}

.paper-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #1E293B;
  line-height: 1.4;
}

.paper-chapter {
  margin-bottom: 48px;
}

.chapter-title {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid #3a5fd9;
  color: #1E293B;
  position: relative;
}

.chapter-title::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 60px;
  height: 2px;
  background: linear-gradient(90deg, #3a5fd9, #5d7ef2);
}

.paper-section {
  margin-bottom: 32px;
  padding: 20px;
  border-radius: 8px;
  background: #FAFCFF;
  border: 1px solid var(--border-light);
  transition: all 0.2s ease;
}

.paper-section:hover {
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 17px;
  font-weight: 600;
  color: #334155;
  position: relative;
  padding-left: 12px;
}

.section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 18px;
  background: linear-gradient(180deg, #3a5fd9, #5d7ef2);
  border-radius: 2px;
}

.section-actions {
  display: flex;
  gap: 8px;
}

.section-loading-box {
  padding: 20px;
}

.loading-skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, #dce6f8 25%, #edf3fd 50%, #dce6f8 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

.skeleton-line.short {
  width: 60%;
}

.skeleton-line.skeleton-title {
  height: 20px;
  width: 40%;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.section-empty {
  padding: 32px;
  text-align: center;
}

.empty-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #94A3B8;
}

.pending-lines {
  width: min(560px, 92%);
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.pending-lines .line {
  display: block;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #dce6f8 10%, #eef3fc 50%, #dce6f8 90%);
  background-size: 220% 100%;
  animation: pendingShimmer 1.8s linear infinite;
}

.pending-lines .line.title {
  width: 38%;
  height: 14px;
}

.pending-lines .line.short {
  width: 56%;
}

.empty-placeholder p {
  font-size: 14px;
  margin: 0;
}

.section-content {
  animation: fadeIn 0.3s ease;
}

.section-streaming {
  position: relative;
  animation: fadeIn 0.2s ease;
}

.streaming-content {
  font-size: 15px;
  line-height: 1.8;
  color: #374151;
  text-align: justify;
  white-space: pre-wrap;
  font-family: 'Georgia', 'Times New Roman', serif;
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #3a5fd9 0%, #5d7ef2 100%);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  width: fit-content;
  animation: pulse 1.5s ease-in-out infinite;
}

.streaming-indicator .loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pendingShimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.content-text {
  font-size: 15px;
  line-height: 1.8;
  color: #374151;
  text-align: justify;
  white-space: pre-wrap;
  font-family: 'Georgia', 'Times New Roman', serif;
}

.word-count {
  margin-top: 16px;
  font-size: 12px;
  color: #94A3B8;
  text-align: right;
}

.empty-outline {
  padding: 60px 0;
}

.paper-detail :deep(.el-button--primary) {
  background: linear-gradient(135deg, #3a5fd9 0%, #5d7ef2 100%) !important;
  border: none !important;
  box-shadow: var(--shadow-sm);
}

.paper-detail :deep(.el-button--warning) {
  background: linear-gradient(135deg, #c68e32 0%, #e4ac53 100%) !important;
  border: none !important;
}
</style>
