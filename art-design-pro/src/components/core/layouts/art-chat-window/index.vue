<!-- AI 对话窗口 — 多会话、流式回复、RAG -->
<template>
  <div>
    <ElDrawer
      v-model="isDrawerVisible"
      :size="isMobile ? '100%' : '520px'"
      :with-header="false"
      @opened="onDrawerOpened"
    >
      <div class="flex h-full flex-col">
        <!-- ─── 顶部栏 ─── -->
        <div class="flex-cb border-b-d px-4 py-3">
          <div class="flex-c gap-2">
            <span class="text-base font-medium">AI 助手</span>
            <ElTag v-if="activeSession" size="small" type="info">
              {{ activeSession.model_name || '未配置模型' }}
            </ElTag>
          </div>
          <div class="flex-c gap-1">
            <ElTooltip content="新建对话" placement="bottom">
              <ElIcon class="c-p p-1 hover:text-theme" :size="18" @click="createNewSession">
                <Plus />
              </ElIcon>
            </ElTooltip>
            <ElTooltip content="管理文档" placement="bottom">
              <ElIcon class="c-p p-1 hover:text-theme" :size="18" @click="showDocPanel = !showDocPanel">
                <Document />
              </ElIcon>
            </ElTooltip>
            <ElIcon class="c-p p-1 hover:text-theme" :size="18" @click="closeChat">
              <Close />
            </ElIcon>
          </div>
        </div>

        <!-- ─── 会话列表 (折叠区) ─── -->
        <div v-if="showSessionList" class="max-h-50 overflow-y-auto border-b-d bg-g-100/50">
          <div
            v-for="s in sessions"
            :key="s.id"
            class="flex-cb cursor-pointer px-4 py-2.5 text-sm transition-colors hover:bg-g-200/60"
            :class="{ '!bg-theme/10 font-medium': s.id === activeSession?.id }"
            @click="switchSession(s)"
          >
            <span class="flex-1 truncate">{{ s.title }}</span>
            <ElIcon
              class="ml-2 shrink-0 text-g-500 hover:text-danger"
              :size="14"
              @click.stop="deleteSession(s.id)"
            >
              <Delete />
            </ElIcon>
          </div>
          <div v-if="sessions.length === 0" class="py-4 text-center text-xs text-g-500">
            暂无对话，点击 + 创建
          </div>
        </div>

        <!-- 会话列表开关 -->
        <div
          class="flex-c cursor-pointer gap-1 border-b-d px-4 py-1.5 text-xs text-g-500 hover:text-theme"
          @click="showSessionList = !showSessionList"
        >
          <ElIcon :size="12">
            <component :is="showSessionList ? ArrowUp : ArrowDown" />
          </ElIcon>
          <span>{{ showSessionList ? '收起会话' : `会话列表 (${sessions.length})` }}</span>
        </div>

        <!-- ─── 文档管理面板 ─── -->
        <div v-if="showDocPanel" class="max-h-48 overflow-y-auto border-b-d bg-g-50/80 px-4 py-3">
          <div class="mb-2 flex-cb text-xs">
            <span class="font-medium">RAG 文档</span>
            <label class="cursor-pointer text-theme hover:underline">
              上传文件
              <input type="file" class="hidden" accept=".txt,.md,.pdf,.docx" @change="handleFileUpload" />
            </label>
          </div>
          <div v-for="doc in documents" :key="doc.id" class="mb-1.5 flex-cb rounded bg-white px-2.5 py-1.5 text-xs">
            <div class="flex-c gap-1.5 overflow-hidden">
              <ElIcon :size="14" class="shrink-0 text-g-500"><Document /></ElIcon>
              <span class="truncate">{{ doc.filename }}</span>
              <ElTag :type="doc.status === 'ready' ? 'success' : doc.status === 'error' ? 'danger' : 'warning'" size="small">
                {{ doc.status === 'ready' ? '就绪' : doc.status === 'error' ? '失败' : '处理中' }}
              </ElTag>
            </div>
            <ElIcon class="shrink-0 cursor-pointer text-g-400 hover:text-danger" :size="14" @click="removeDocument(doc.id)">
              <Delete />
            </ElIcon>
          </div>
          <div v-if="documents.length === 0" class="py-2 text-center text-xs text-g-400">暂无文档</div>
          <div class="mt-2 flex-c gap-2 text-xs">
            <ElCheckbox v-model="enableRag" size="small" label="启用 RAG" />
          </div>
        </div>

        <!-- ─── 聊天消息区域 ─── -->
        <div ref="messageContainer" class="flex-1 overflow-y-auto px-4 py-5 [&::-webkit-scrollbar]:!w-1">
          <template v-if="messages.length === 0 && !isStreaming">
            <div class="flex h-full flex-col items-center justify-center text-g-400">
              <ElIcon :size="48" class="mb-3"><ChatDotRound /></ElIcon>
              <p class="text-sm">开始一段新的对话吧</p>
            </div>
          </template>

          <template v-for="(msg, idx) in messages" :key="idx">
            <div :class="['mb-5 flex w-full items-start gap-2.5', msg.role === 'user' ? 'flex-row-reverse' : 'flex-row']">
              <div
                class="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                :class="msg.role === 'user' ? 'bg-theme' : 'bg-g-600'"
              >
                {{ msg.role === 'user' ? 'U' : 'AI' }}
              </div>
              <div :class="['max-w-[80%]', msg.role === 'user' ? 'text-right' : 'text-left']">
                <div
                  :class="[
                    'inline-block whitespace-pre-wrap rounded-lg px-3.5 py-2.5 text-sm leading-relaxed',
                    msg.role === 'user' ? 'bg-theme/15 text-g-900' : 'bg-g-200/60 text-g-900'
                  ]"
                >{{ msg.content }}<span v-if="isStreaming && idx === messages.length - 1 && msg.role === 'assistant'" class="animate-pulse">▌</span></div>
              </div>
            </div>
          </template>
        </div>

        <!-- ─── 输入区域 ─── -->
        <div class="border-t-d px-4 py-3">
          <div class="flex items-end gap-2">
            <ElInput
              v-model="messageText"
              type="textarea"
              :rows="2"
              :autosize="{ minRows: 1, maxRows: 5 }"
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
              resize="none"
              :disabled="isStreaming"
              @keydown="handleKeydown"
            />
            <ElButton
              type="primary"
              :icon="isStreaming ? Loading : Promotion"
              :loading="isStreaming"
              :disabled="!messageText.trim() && !isStreaming"
              circle
              @click="isStreaming ? stopStream() : sendMessage()"
            />
          </div>
        </div>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import {
  Close,
  Plus,
  Delete,
  Document,
  ArrowUp,
  ArrowDown,
  Promotion,
  Loading,
  ChatDotRound
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { mittBus } from '@/utils/sys'
import {
  fetchSessions,
  fetchCreateSession,
  fetchDeleteSession,
  fetchMessages,
  fetchDocuments,
  fetchUploadDocument,
  fetchDeleteDocument,
  streamChat,
  type ChatSession,
  type ChatMessage,
  type ChatDocument,
} from '@/api/chat'

defineOptions({ name: 'ArtChatWindow' })

const MOBILE_BREAKPOINT = 640
const { width } = useWindowSize()
const isMobile = computed(() => width.value < MOBILE_BREAKPOINT)

const isDrawerVisible = ref(false)
const messageText = ref('')
const messageContainer = ref<HTMLElement | null>(null)
const isStreaming = ref(false)
let abortController: AbortController | null = null

const showSessionList = ref(false)
const showDocPanel = ref(false)
const enableRag = ref(false)

const sessions = ref<ChatSession[]>([])
const activeSession = ref<ChatSession | null>(null)
const messages = ref<ChatMessage[]>([])
const documents = ref<ChatDocument[]>([])

// ─── 会话管理 ────────────────────────

async function loadSessions() {
  try {
    sessions.value = await fetchSessions()
  } catch {
    sessions.value = []
  }
}

async function createNewSession() {
  try {
    const s = await fetchCreateSession({ title: '新对话' })
    sessions.value.unshift(s)
    await switchSession(s)
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  }
}

async function switchSession(s: ChatSession) {
  activeSession.value = s
  showSessionList.value = false
  try {
    messages.value = await fetchMessages(s.id)
  } catch {
    messages.value = []
  }
  scrollToBottom()
}

async function deleteSession(id: number) {
  try {
    await fetchDeleteSession(id)
    sessions.value = sessions.value.filter((s) => s.id !== id)
    if (activeSession.value?.id === id) {
      activeSession.value = sessions.value[0] || null
      if (activeSession.value) {
        messages.value = await fetchMessages(activeSession.value.id)
      } else {
        messages.value = []
      }
    }
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

// ─── 消息发送 ────────────────────────

async function sendMessage() {
  const text = messageText.value.trim()
  if (!text || isStreaming.value) return

  if (!activeSession.value) {
    await createNewSession()
    if (!activeSession.value) return
  }

  messages.value.push({ id: 0, role: 'user', content: text, created_at: '' })
  messageText.value = ''
  scrollToBottom()

  messages.value.push({ id: 0, role: 'assistant', content: '', created_at: '' })
  isStreaming.value = true

  const assistantIdx = messages.value.length - 1
  const docIds = enableRag.value ? documents.value.filter((d) => d.status === 'ready').map((d) => d.id) : []

  abortController = await streamChat(
    activeSession.value.id,
    {
      content: text,
      enable_rag: enableRag.value && docIds.length > 0,
      document_ids: docIds
    },
    (token) => {
      messages.value[assistantIdx].content += token
      scrollToBottom()
    },
    () => {
      isStreaming.value = false
      loadSessions()
    },
    (errMsg) => {
      isStreaming.value = false
      if (!messages.value[assistantIdx].content) {
        messages.value[assistantIdx].content = `⚠️ ${errMsg}`
      }
    }
  )
}

function stopStream() {
  abortController?.abort()
  isStreaming.value = false
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ─── 文档管理 ────────────────────────

async function loadDocuments() {
  try {
    documents.value = await fetchDocuments()
  } catch {
    documents.value = []
  }
}

async function handleFileUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''
  try {
    const doc = await fetchUploadDocument(file)
    documents.value.unshift(doc)
    ElMessage.success('文件上传成功，正在处理...')
    setTimeout(loadDocuments, 5000)
  } catch (err: any) {
    ElMessage.error(err.message || '上传失败')
  }
}

async function removeDocument(id: number) {
  try {
    await fetchDeleteDocument(id)
    documents.value = documents.value.filter((d) => d.id !== id)
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

// ─── UI helpers ──────────────────────

function scrollToBottom() {
  nextTick(() => {
    setTimeout(() => {
      if (messageContainer.value) {
        messageContainer.value.scrollTop = messageContainer.value.scrollHeight
      }
    }, 50)
  })
}

async function onDrawerOpened() {
  await Promise.all([loadSessions(), loadDocuments()])
  if (sessions.value.length > 0 && !activeSession.value) {
    await switchSession(sessions.value[0])
  }
  scrollToBottom()
}

function openChat() {
  isDrawerVisible.value = true
}
function closeChat() {
  isDrawerVisible.value = false
}

onMounted(() => {
  mittBus.on('openChat', openChat)
})
onUnmounted(() => {
  mittBus.off('openChat', openChat)
})
</script>
