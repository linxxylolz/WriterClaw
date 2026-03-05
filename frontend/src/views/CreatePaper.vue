<template>
  <div class="create-page">
    <div class="steps-container">
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="基本信息" />
        <el-step title="生成大纲" />
        <el-step title="灵感预览" />
      </el-steps>
    </div>

    <div class="step-content">
      <div v-show="currentStep === 0" class="step-panel">
        <el-form :model="form" label-width="100px" class="paper-form">
          <el-form-item label="灵感标题" required>
            <el-input
              v-model="form.title"
              placeholder="请输入灵感标题"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="灵感类型" required>
            <el-select v-model="form.paper_type" placeholder="请选择灵感类型">
              <el-option label="毕业报告" value="graduation" />
              <el-option label="课程报告" value="course" />
              <el-option label="开题报告" value="proposal" />
              <el-option label="文献综述" value="review" />
            </el-select>
          </el-form-item>

          <el-form-item label="文稿方向" required>
            <el-radio-group v-model="form.direction" class="direction-group">
              <el-radio-button value="finance">
                <div class="direction-option">
                  <el-icon><Money /></el-icon>
                  <span>财务管理</span>
                </div>
              </el-radio-button>
              <el-radio-button value="business">
                <div class="direction-option">
                  <el-icon><OfficeBuilding /></el-icon>
                  <span>工商管理</span>
                </div>
              </el-radio-button>
              <el-radio-button value="hr">
                <div class="direction-option">
                  <el-icon><User /></el-icon>
                  <span>人力资源</span>
                </div>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="专业">
            <el-input v-model="form.major" placeholder="请输入专业" />
          </el-form-item>

          <el-form-item label="关键词">
            <el-select
              v-model="form.keywords"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入关键词后按回车添加"
              style="width: 100%"
            >
              <el-option
                v-for="keyword in form.keywords"
                :key="keyword"
                :label="keyword"
                :value="keyword"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="字数要求">
            <el-input-number
              v-model="form.word_count"
              :min="3000"
              :max="50000"
              :step="1000"
            />
            <span class="hint">字</span>
          </el-form-item>

          <el-form-item label="自定义引导词">
            <el-input
              v-model="form.customPrompt"
              type="textarea"
              :rows="3"
              placeholder="可选：输入自定义引导词，AI将参考此内容生成文章"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="nextStep" :disabled="!form.title">
              下一步：生成大纲
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-show="currentStep === 1" class="step-panel">
        <div class="outline-header">
          <h3>灵感大纲</h3>
          <div class="outline-actions">
            <el-button @click="currentStep = 0">上一步</el-button>
            <el-button type="primary" @click="generateOutline" :loading="generating" :disabled="generating || !!generatingSection">
              <el-icon><Refresh /></el-icon>
              重新生成
            </el-button>
            <el-button type="success" @click="confirmOutline" :loading="confirmingOutline" :disabled="!outline.length || generating || !!generatingSection || confirmingOutline">
              {{ confirmingOutline ? '正在开始出稿...' : '确认大纲' }}
            </el-button>
          </div>
        </div>

        <div class="outline-tree" v-if="outline.length > 0">
          <div 
            v-for="(chapter, chIndex) in outline" 
            :key="chapter.id" 
            class="chapter-item"
            :style="{ animationDelay: `${chIndex * 0.1}s` }"
          >
            <div class="chapter-header">
              <span class="chapter-number">{{ chIndex + 1 }}</span>
              <el-input
                v-model="chapter.title"
                class="chapter-title-input"
                @blur="saveOutline"
              />
              <el-button text type="danger" @click="removeChapter(chIndex)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="sections-list">
              <div
                v-for="(section, secIndex) in chapter.sections"
                :key="section.id"
                class="section-item"
                :style="{ animationDelay: `${(chIndex * 0.1) + (secIndex * 0.05)}s` }"
              >
                <span class="section-number">{{ chIndex + 1 }}.{{ secIndex + 1 }}</span>
                <el-input
                  v-model="section.title"
                  class="section-title-input"
                  @blur="saveOutline"
                />
                <el-button text type="danger" size="small" @click="removeSection(chIndex, secIndex)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <el-button text size="small" @click="addSection(chIndex)">
                <el-icon><Plus /></el-icon>
                添加小节
              </el-button>
            </div>
          </div>
        </div>

        <el-empty v-else description="点击上方按钮生成大纲">
          <el-button type="primary" @click="generateOutline" :loading="generating" :disabled="generating || !!generatingSection">
            生成大纲
          </el-button>
        </el-empty>
      </div>

      <div v-show="currentStep === 2" class="step-panel">
        <div class="preview-header">
          <h3>灵感预览</h3>
          <div class="preview-actions">
            <el-button @click="currentStep = 1">返回大纲</el-button>
            <el-button type="primary" @click="exportWord" :disabled="!!generatingSection || generating">
              <el-icon><Download /></el-icon>
              导出Word
            </el-button>
          </div>
        </div>

        <div class="paper-viewer">
          <div class="viewer-sidebar">
            <el-scrollbar>
              <div class="outline-nav">
                <div
                  v-for="(chapter, chIndex) in paper?.outline || []"
                  :key="chapter.id"
                  class="nav-chapter"
                >
                  <div
                    class="nav-chapter-title"
                    :class="{ active: activeChapter === chIndex }"
                    @click="scrollToChapter(chIndex)"
                  >
                    {{ chapter.title }}
                  </div>
                  <div class="nav-sections">
                    <div
                      v-for="(section, secIndex) in chapter.sections"
                      :key="section.id"
                      class="nav-section"
                      :class="{ active: activeSection === `${chIndex}-${secIndex}`, filled: !!section.content }"
                      @click="scrollToSection(chIndex, secIndex)"
                    >
                      {{ section.title }}
                    </div>
                  </div>
                </div>
              </div>
            </el-scrollbar>
          </div>

          <div class="viewer-content">
            <el-scrollbar>
              <div class="paper-content" ref="paperContentRef">
                <h1 class="paper-title">{{ paper?.title }}</h1>
                <div
                  v-for="(chapter, chIndex) in paper?.outline || []"
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
                          :loading="generatingSection === section.id"
                          :disabled="!!generatingSection && generatingSection !== section.id"
                          @click="generateSection(chapter.id, section.id)"
                        >
                          {{ section.content ? '重新生成' : '生成内容' }}
                        </el-button>
                        <el-button
                          size="small"
                          type="warning"
                          @click="openRefineDialog(chIndex, secIndex)"
                          :disabled="!section.content || !!generatingSection"
                        >
                          微调
                        </el-button>
                      </div>
                    </div>
                    <div v-if="!section.content && generatingSection !== section.id" class="section-pending">
                      <div class="pending-lines">
                        <span class="line title"></span>
                        <span class="line"></span>
                        <span class="line"></span>
                        <span class="line short"></span>
                      </div>
                      <p>该小节尚未生成，点击上方“生成内容”开始实时写作</p>
                    </div>
                    <div v-else-if="!section.content && generatingSection === section.id" class="section-pending is-generating">
                      <div class="pending-lines">
                        <span class="line title"></span>
                        <span class="line"></span>
                        <span class="line"></span>
                        <span class="line short"></span>
                      </div>
                      <p>正在实时生成内容...</p>
                    </div>
                    <el-input
                      v-else
                      v-model="section.content"
                      type="textarea"
                      :rows="8"
                      :disabled="generatingSection === section.id"
                      placeholder="点击上方按钮生成内容，或直接在此编辑"
                      @blur="saveSection(chapter.id, section)"
                    />
                    <div class="word-count">字数: {{ section.word_count || 0 }}</div>
                  </div>
                </div>
                <div class="word-count total-word-count" v-if="paper">
                  总字数进度：{{ paper.generated_word_count || 0 }} / {{ paper.target_word_count || paper.word_count || 0 }}
                </div>
              </div>
            </el-scrollbar>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="refineDialogVisible" title="段落微调" width="600px">
      <el-form>
        <el-form-item label="微调指令">
          <el-input
            v-model="refineInstruction"
            type="textarea"
            :rows="3"
            placeholder="请输入微调要求，如：'简化内容'、'增加案例'、'改写得更正式'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="refineDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="refineSection" :loading="refining">
          确认微调
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
import { Refresh, Delete, Plus, Download, Money, OfficeBuilding, User } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const paperStore = usePaperStore()

const currentStep = ref(0)
const form = ref({
  title: '',
  paper_type: 'graduation',
  direction: 'finance',
  major: '',
  keywords: [],
  word_count: 10000,
  customPrompt: ''
})

const paper = computed(() => paperStore.currentPaper)
const generating = computed(() => paperStore.generating)
const generatingSection = ref(null)
const refining = ref(false)

const outline = ref([])
const activeChapter = ref(0)
const activeSection = ref('0-0')
const paperContentRef = ref(null)

const refineDialogVisible = ref(false)
const refineInstruction = ref('')
const refineTarget = ref({ chapterIndex: 0, sectionIndex: 0 })
const confirmingOutline = ref(false)

onMounted(async () => {
  const paperId = route.query.paperId
  if (paperId) {
    const paperData = await paperStore.fetchPaper(paperId)
    if (paperData) {
      form.value = {
        title: paperData.title,
        paper_type: paperData.paper_type,
        direction: paperData.direction || 'finance',
        major: paperData.major,
        keywords: paperData.keywords || [],
        word_count: paperData.word_count || 10000,
        customPrompt: paperData.custom_prompt || ''
      }
      outline.value = paperData.outline || []
      if (paperData.outline && paperData.outline.length > 0) {
        currentStep.value = 2
      } else if (paperData.status === 'outline_generated') {
        currentStep.value = 1
      }
    }
  }
})

const nextStep = async () => {
  const paperData = await paperStore.createPaper(form.value)
  if (paperData) {
    router.push(`/create?paperId=${paperData.id}`)
    currentStep.value = 1
  }
}

const generateOutline = async () => {
  if (!paper.value) return
  const result = await paperStore.generateOutline(paper.value.id)
  if (result) {
    outline.value = result.outline || []
    ElMessage.success('大纲生成成功')
  }
}

const saveOutline = async () => {
  if (!paper.value) return
  await paperStore.updateOutline(paper.value.id, outline.value)
}

const confirmOutline = async () => {
  if (!paper.value) return
  try {
    confirmingOutline.value = true
    currentStep.value = 2
    await router.push({
      path: `/paper/${paper.value.id}`,
      query: { autoGenerate: '1' }
    })
  } finally {
    confirmingOutline.value = false
  }
}

const addChapter = () => {
  const newId = `ch${outline.value.length + 1}`
  outline.value.push({
    id: newId,
    title: '新章节',
    sections: []
  })
  saveOutline()
}

const removeChapter = (index) => {
  outline.value.splice(index, 1)
  saveOutline()
}

const addSection = (chIndex) => {
  const chapter = outline.value[chIndex]
  const newId = `${chapter.id}-${chapter.sections.length + 1}`
  chapter.sections.push({
    id: newId,
    title: '新小节',
    content: '',
    word_count: 0
  })
  saveOutline()
}

const removeSection = (chIndex, secIndex) => {
  outline.value[chIndex].sections.splice(secIndex, 1)
  saveOutline()
}

const generateSection = async (chapterId, sectionId) => {
  if (!paper.value) return
  try {
    generatingSection.value = sectionId
    await paperStore.generateSection(paper.value.id, chapterId, sectionId, (content) => {
      const chapter = paper.value?.outline?.find(ch => ch.id === chapterId)
      const section = chapter?.sections?.find(sec => sec.id === sectionId)
      if (section) {
        section.content = content
        section.word_count = content.length
      }
    })
  } finally {
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
  element?.scrollIntoView({ behavior: 'smooth' })
}

const scrollToSection = (chIndex, secIndex) => {
  activeChapter.value = chIndex
  activeSection.value = `${chIndex}-${secIndex}`
  const element = document.getElementById(`section-${chIndex}-${secIndex}`)
  element?.scrollIntoView({ behavior: 'smooth' })
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
.create-page {
  height: 100%;
  min-height: 0;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.steps-container {
  background: #FFFFFF;
  padding: 28px 32px;
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  flex-shrink: 0;
}

.steps-container :deep(.el-step__title) {
  font-weight: 500;
}

.steps-container :deep(.el-step__title.is-process) {
  color: #667eea;
}

.steps-container :deep(.el-step__title.is-finish) {
  color: #10B981;
}

.step-content {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.step-panel {
  animation: slideUp 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

@keyframes slideUp {
  from { 
    opacity: 0; 
    transform: translateY(20px); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0); 
  }
}

.paper-form {
  max-width: 700px;
}

.paper-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #374151;
}

.paper-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 4px 12px;
  box-shadow: 0 0 0 1px #E2E8F0 inset;
  transition: all 0.3s ease;
}

.paper-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #CBD5E1 inset;
}

.paper-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2), 0 0 0 1px #667eea inset;
}

.paper-form :deep(.el-select .el-input__wrapper) {
  border-radius: 12px;
}

.direction-group {
  display: flex;
  gap: 16px;
}

.direction-group .el-radio-button {
  flex: 1;
}

.direction-group .el-radio-button__inner {
  width: 100%;
  padding: 20px 16px;
  border-radius: 12px !important;
  transition: all 0.3s ease;
}

.direction-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.direction-option .el-icon {
  font-size: 28px;
  color: #667eea;
  transition: all 0.3s ease;
}

.direction-option span {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  transition: all 0.3s ease;
}

.direction-group .el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  border-color: #667eea !important;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.direction-group .el-radio-button__original-radio:checked + .el-radio-button__inner .direction-option .el-icon {
  color: white;
  transform: scale(1.1);
}

.direction-group .el-radio-button__original-radio:checked + .el-radio-button__inner .direction-option span {
  color: white;
}

.direction-group .el-radio-button__original-radio:not(:checked) + .el-radio-button__inner:hover {
  background: #F8FAFC;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.hint {
  margin-left: 12px;
  color: #94A3B8;
  font-size: 14px;
}

.paper-form :deep(.el-button--primary) {
  height: 48px;
  padding: 0 32px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
}

.paper-form :deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.paper-form :deep(.el-button--primary:active) {
  transform: translateY(0);
}

.outline-header,
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
  padding-bottom: 16px;
  border-bottom: 2px solid #F1F5F9;
  flex-shrink: 0;
}

.outline-header h3,
.preview-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1E293B;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.outline-actions,
.preview-actions {
  display: flex;
  gap: 12px;
}

.outline-actions :deep(.el-button),
.preview-actions :deep(.el-button) {
  border-radius: 10px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.outline-actions :deep(.el-button--primary),
.preview-actions :deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.outline-actions :deep(.el-button--primary:hover),
.preview-actions :deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.outline-actions :deep(.el-button--success),
.preview-actions :deep(.el-button--success) {
  background: linear-gradient(135deg, #10B981 0%, #34D399 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.outline-actions :deep(.el-button--success:hover),
.preview-actions :deep(.el-button--success:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
}

.outline-tree {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chapter-item {
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 20px;
  background: #FAFBFC;
  transition: all 0.3s ease;
  animation: outlineSlideIn 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
  opacity: 0;
  filter: blur(8px);
}

@keyframes outlineSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
    filter: blur(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}

.chapter-item:hover {
  border-color: rgba(102, 126, 234, 0.3);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.chapter-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}

.chapter-number {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  animation: numberPopIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

@keyframes numberPopIn {
  0% {
    opacity: 0;
    transform: scale(0);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.chapter-title-input {
  flex: 1;
  max-width: 450px;
}

.chapter-title-input :deep(.el-input__wrapper) {
  border-radius: 8px;
}

.chapter-title-input :deep(.el-input__inner) {
  font-weight: 600;
}

.sections-list {
  padding-left: 46px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
  animation: sectionSlideIn 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
  opacity: 0;
  filter: blur(6px);
}

@keyframes sectionSlideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
    filter: blur(6px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
    filter: blur(0);
  }
}

.section-item:hover {
  background: rgba(102, 126, 234, 0.05);
}

.section-number {
  color: #94A3B8;
  font-size: 13px;
  min-width: 28px;
  font-weight: 500;
}

.section-title-input {
  flex: 1;
  max-width: 380px;
}

.section-title-input :deep(.el-input__wrapper) {
  border-radius: 8px;
}

.paper-viewer {
  display: flex;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.viewer-sidebar {
  width: 260px;
  background: linear-gradient(180deg, #f8faff 0%, #f1f6ff 100%);
  border-right: 1px solid var(--border-light);
}

.outline-nav {
  padding: 16px;
}

.nav-chapter {
  margin-bottom: 6px;
}

.nav-chapter-title {
  padding: 10px 14px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  color: #374151;
}

.nav-chapter-title:hover {
  background: rgba(58, 95, 217, 0.1);
  color: #3a5fd9;
}

.nav-chapter-title.active {
  background: linear-gradient(135deg, #3a5fd9 0%, #5d7ef2 100%);
  color: #FFFFFF;
  box-shadow: 0 6px 16px rgba(58, 95, 217, 0.24);
}

.nav-sections {
  padding-left: 14px;
  margin-top: 4px;
}

.nav-section {
  padding: 8px 14px;
  font-size: 13px;
  color: #64748B;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-section:hover {
  background: rgba(58, 95, 217, 0.08);
  color: #374151;
}

.nav-section.active {
  background: rgba(58, 95, 217, 0.14);
  color: #3a5fd9;
}

.nav-section.filled {
  color: #10B981;
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
  padding: 36px;
  max-width: 850px;
  margin: 0 auto;
}

.paper-title {
  text-align: center;
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 36px;
  color: #1E293B;
  line-height: 1.4;
  padding-bottom: 20px;
  border-bottom: 2px solid #E2E8F0;
}

.paper-chapter {
  margin-bottom: 40px;
}

.chapter-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #667eea;
  color: #1E293B;
  position: relative;
}

.chapter-title::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 50px;
  height: 2px;
  background: linear-gradient(90deg, #667eea, #764ba2);
}

.paper-section {
  margin-bottom: 28px;
  padding: 20px;
  border-radius: 10px;
  background: #FAFBFC;
  border: 1px solid #F1F5F9;
  transition: all 0.2s ease;
}

.paper-section:hover {
  border-color: rgba(102, 126, 234, 0.2);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #334155;
}

.section-actions {
  display: flex;
  gap: 8px;
}

.section-actions :deep(.el-button) {
  border-radius: 8px;
  font-weight: 500;
}

.section-actions :deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.section-actions :deep(.el-button--warning) {
  background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%);
  border: none;
}

.paper-section :deep(.el-textarea__inner) {
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  background: #FFFFFF;
}

.paper-section :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2), 0 0 0 1px #667eea inset;
}

.word-count {
  margin-top: 10px;
  font-size: 12px;
  color: #94A3B8;
  text-align: right;
}

.total-word-count {
  margin-top: 20px;
  font-size: 13px;
  color: #64748B;
  text-align: center;
}

.section-pending {
  padding: 18px;
  border-radius: 12px;
  border: 1px dashed #ced8ec;
  background: linear-gradient(180deg, #f8faff 0%, #f3f7ff 100%);
}

.section-pending p {
  margin: 10px 0 0;
  font-size: 13px;
  color: #64748b;
}

.pending-lines {
  display: grid;
  gap: 9px;
}

.pending-lines .line {
  display: block;
  height: 11px;
  border-radius: 999px;
  background: linear-gradient(90deg, #dce6f8 10%, #eef3fc 50%, #dce6f8 90%);
  background-size: 220% 100%;
  animation: pendingShimmer 1.8s linear infinite;
}

.pending-lines .line.title {
  width: 42%;
  height: 15px;
}

.pending-lines .line.short {
  width: 58%;
}

.section-pending.is-generating {
  border-color: rgba(58, 95, 217, 0.4);
  box-shadow: 0 0 0 1px rgba(58, 95, 217, 0.12) inset;
}

@keyframes pendingShimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.empty-outline {
  padding: 80px 0;
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.preview-actions {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #E2E8F0;
}

.create-page :deep(.el-button--primary),
.section-actions :deep(.el-button--primary),
.outline-actions :deep(.el-button--primary),
.preview-actions :deep(.el-button--primary) {
  background: linear-gradient(135deg, #3a5fd9 0%, #5d7ef2 100%) !important;
  border: none !important;
  box-shadow: var(--shadow-sm);
}

.create-page :deep(.el-button--warning),
.section-actions :deep(.el-button--warning) {
  background: linear-gradient(135deg, #c68e32 0%, #e4ac53 100%) !important;
  border: none !important;
}

.chapter-item,
.paper-section,
.step-content,
.steps-container,
.paper-viewer {
  border-color: var(--border-light);
  box-shadow: var(--shadow-sm);
}

@media (max-width: 768px) {
  .create-page {
    padding: 0 16px;
  }
  
  .steps-container,
  .step-content {
    padding: 20px;
    border-radius: 12px;
  }
  
  .direction-group {
    flex-direction: column;
  }
  
  .paper-viewer {
    flex-direction: column;
    height: auto;
  }
  
  .viewer-sidebar {
    width: 100%;
    height: 200px;
  }
}
</style>
