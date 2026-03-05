import { defineStore } from 'pinia'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

const checkApiKey = () => {
  const apiKey = localStorage.getItem('minimaxApiKey')
  if (!apiKey || apiKey.trim() === '') {
    return false
  }
  return true
}

const sanitizeThinkContent = (text = '') => {
  if (!text) return text
  let cleaned = text
    .replace(/<\s*think\b[^>]*>[\s\S]*?<\s*\/\s*think\s*>/gi, '')
    .replace(/<\s*think\b[^>]*>[\s\S]*$/gi, '')
    .replace(/```(?:thinking|think)[\s\S]*?```/gi, '')
    .replace(/<｜tool▁calls｜>[\s\S]*$/g, '')

  return cleaned
}

export const usePaperStore = defineStore('paper', {
  state: () => ({
    papers: [],
    currentPaper: null,
    loading: false,
    generating: false
  }),

  actions: {
    syncPaperToList(updatedPaper) {
      if (!updatedPaper?.id) return
      const index = this.papers.findIndex(p => p.id === updatedPaper.id)
      if (index !== -1) {
        this.papers[index] = updatedPaper
      }
    },

    async fetchPapers() {
      this.loading = true
      try {
        const res = await api.get('/papers')
        this.papers = res.data
      } catch (error) {
        console.error('Failed to fetch papers:', error)
      } finally {
        this.loading = false
      }
    },

    async fetchPaper(id) {
      this.loading = true
      try {
        const res = await api.get(`/papers/${id}`)
        this.currentPaper = res.data
        return res.data
      } catch (error) {
        console.error('Failed to fetch paper:', error)
        return null
      } finally {
        this.loading = false
      }
    },

    async createPaper(data) {
      try {
        const payload = {
          ...data,
          custom_prompt: data?.customPrompt ?? data?.custom_prompt ?? ''
        }
        delete payload.customPrompt

        const res = await api.post('/papers', payload)
        this.papers.unshift(res.data)
        this.currentPaper = res.data
        return res.data
      } catch (error) {
        console.error('Failed to create paper:', error)
        return null
      }
    },

    async generateOutline(paperId) {
      if (!checkApiKey()) {
        console.error('No API key configured')
        return { error: 'no_api_key' }
      }
      this.generating = true
      try {
        const apiKey = localStorage.getItem('minimaxApiKey')
        const res = await api.post(`/papers/${paperId}/outline`, {}, {
          params: { api_key: apiKey }
        })
        this.currentPaper = res.data
        this.syncPaperToList(res.data)
        return res.data
      } catch (error) {
        console.error('Failed to generate outline:', error)
        return null
      } finally {
        this.generating = false
      }
    },

    async updateOutline(paperId, outline) {
      try {
        const res = await api.put(`/papers/${paperId}/outline`, { outline })
        this.currentPaper = res.data
        this.syncPaperToList(res.data)
        return res.data
      } catch (error) {
        console.error('Failed to update outline:', error)
        return null
      }
    },

    async generateSection(paperId, chapterId, sectionId, onChunk) {
      this.generating = true
      try {
        const apiKey = localStorage.getItem('minimaxApiKey')
        const response = await fetch(`/api/papers/${paperId}/sections/${chapterId}/${sectionId}/generate?api_key=${encodeURIComponent(apiKey)}`, {
          method: 'POST',
          headers: {
            Accept: 'text/event-stream'
          }
        })
        
        if (!response.ok) {
          throw new Error('Failed to generate section')
        }

        if (!response.body) {
          throw new Error('Empty stream response')
        }
        
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let fullContent = ''
        let buffer = ''
        
        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            buffer += decoder.decode()
          } else {
            buffer += decoder.decode(value, { stream: true })
          }

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const payload = line.slice(6).trim()
              if (!payload || payload === '[DONE]') continue

              try {
                const data = JSON.parse(payload)
                if (data.content) {
                  fullContent += sanitizeThinkContent(data.content)
                  if (onChunk) onChunk(fullContent)
                }
                if (data.done) {
                  await this.fetchPaper(paperId)
                }
              } catch (e) {
                console.error('Parse error:', e)
              }
            }
          }

          if (done) break
        }
        
        return fullContent
      } catch (error) {
        console.error('Failed to generate section:', error)
        return null
      } finally {
        this.generating = false
      }
    },

    async generateAllSections(paperId, onProgress) {
      this.generating = true
      try {
        const paper = this.currentPaper
        if (!paper || !paper.outline) return
        
        let completed = 0
        const total = paper.outline.reduce((sum, ch) => sum + ch.sections.length, 0)
        
        for (const chapter of paper.outline) {
          for (const section of chapter.sections) {
            if (!section.content || section.content.length < 50) {
              await this.generateSection(paperId, chapter.id, section.id)
              completed++
              if (onProgress) onProgress(completed, total)
            }
          }
        }
        
        return true
      } catch (error) {
        console.error('Failed to generate all sections:', error)
        return false
      } finally {
        this.generating = false
      }
    },

    async refineSection(paperId, chapterId, sectionId, instruction) {
      this.generating = true
      try {
        const apiKey = localStorage.getItem('minimaxApiKey')
        const res = await api.post(`/papers/${paperId}/sections/${chapterId}/${sectionId}/refine`, {
          instruction,
          original_content: ''
        }, {
          params: { api_key: apiKey }
        })
        this.currentPaper = res.data
        this.syncPaperToList(res.data)
        return res.data
      } catch (error) {
        console.error('Failed to refine section:', error)
        return null
      } finally {
        this.generating = false
      }
    },

    async updateSection(paperId, chapterId, sectionId, sectionData) {
      try {
        const res = await api.put(`/papers/${paperId}/sections/${chapterId}/${sectionId}`, sectionData)
        this.currentPaper = res.data
        this.syncPaperToList(res.data)
        return res.data
      } catch (error) {
        console.error('Failed to update section:', error)
        return null
      }
    },

    async exportPaper(paperId) {
      try {
        const res = await api.get(`/papers/${paperId}/export`, {
          responseType: 'blob'
        })
        const blob = new Blob([res.data], { 
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        })
        const url = window.URL.createObjectURL(blob)
        const paper = this.currentPaper
        const filename = paper ? `${paper.title}.docx` : '灵感.docx'
        
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        
        return {
          success: true,
          filename
        }
      } catch (error) {
        console.error('Failed to export paper:', error)
        return {
          success: false
        }
      }
    },

    async deletePaper(paperId) {
      try {
        await api.delete(`/papers/${paperId}`)
        this.papers = this.papers.filter(p => p.id !== paperId)
        if (this.currentPaper?.id === paperId) {
          this.currentPaper = null
        }
        return true
      } catch (error) {
        console.error('Failed to delete paper:', error)
        return false
      }
    }
  }
})
