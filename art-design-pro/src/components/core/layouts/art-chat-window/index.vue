<!-- AI 对话窗口 — 多会话、流式回复、RAG、Agent、Markdown -->
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
            <!-- Model switcher -->
            <ElPopover
              v-model:visible="showModelPicker"
              placement="bottom-start"
              :width="260"
              trigger="click"
              @show="loadProviders"
            >
              <template #reference>
                <ElTag class="cursor-pointer" size="small" type="info">
                  {{ activeSession?.model_name || '未配置模型' }}
                  <ElIcon :size="12" class="ml-0.5"><ArrowDown /></ElIcon>
                </ElTag>
              </template>
              <div class="max-h-64 overflow-y-auto">
                <div v-if="providersLoading" class="py-4 text-center text-xs text-g-400"
                  >加载中...</div
                >
                <template v-else>
                  <div v-for="provider in providers" :key="provider.name" class="mb-2">
                    <div class="mb-1 px-1 text-xs font-medium text-g-500">{{
                      provider.display_name
                    }}</div>
                    <div
                      v-for="model in provider.models"
                      :key="model"
                      class="cursor-pointer rounded px-2 py-1.5 text-sm transition-colors hover:bg-theme/10"
                      :class="{
                        'bg-theme/15 font-medium text-theme': activeSession?.model_name === model
                      }"
                      @click="selectModel(provider.name, model)"
                    >
                      {{ model }}
                    </div>
                  </div>
                  <div v-if="providers.length === 0" class="py-4 text-center text-xs text-g-400">
                    暂无可用模型
                  </div>
                </template>
              </div>
            </ElPopover>
          </div>
          <div class="flex-c gap-1">
            <ElTooltip content="新建对话" placement="bottom">
              <ElIcon class="c-p p-1 hover:text-theme" :size="18" @click="createNewSession">
                <Plus />
              </ElIcon>
            </ElTooltip>
            <ElTooltip content="管理文档" placement="bottom">
              <ElIcon
                class="c-p p-1 hover:text-theme"
                :size="18"
                @click="showDocPanel = !showDocPanel"
              >
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
              <input
                type="file"
                class="hidden"
                accept=".txt,.md,.pdf,.docx"
                @change="handleFileUpload"
              />
            </label>
          </div>
          <div
            v-for="doc in documents"
            :key="doc.id"
            class="mb-1.5 flex-cb rounded bg-white px-2.5 py-1.5 text-xs"
          >
            <div class="flex-c gap-1.5 overflow-hidden">
              <ElIcon :size="14" class="shrink-0 text-g-500"><Document /></ElIcon>
              <span class="truncate">{{ doc.filename }}</span>
              <ElTag
                :type="
                  doc.status === 'ready' ? 'success' : doc.status === 'error' ? 'danger' : 'warning'
                "
                size="small"
              >
                {{ doc.status === 'ready' ? '就绪' : doc.status === 'error' ? '失败' : '处理中' }}
              </ElTag>
            </div>
            <div class="flex-c gap-1">
              <ElIcon
                class="shrink-0 cursor-pointer text-g-400 hover:text-theme"
                :size="14"
                @click="previewDocument(doc)"
              >
                <View />
              </ElIcon>
              <ElIcon
                class="shrink-0 cursor-pointer text-g-400 hover:text-danger"
                :size="14"
                @click="removeDocument(doc.id)"
              >
                <Delete />
              </ElIcon>
            </div>
          </div>
          <div v-if="documents.length === 0" class="py-2 text-center text-xs text-g-400"
            >暂无文档</div
          >
          <div class="mt-2 flex-c gap-2 text-xs">
            <ElCheckbox v-model="enableRag" size="small" label="启用 RAG" />
          </div>
        </div>

        <!-- ─── 聊天消息区域 ─── -->
        <div
          ref="messageContainer"
          class="flex-1 overflow-y-auto px-4 py-5 [&::-webkit-scrollbar]:!w-1"
        >
          <template v-if="messages.length === 0 && !isStreaming">
            <div class="flex h-full flex-col items-center justify-center text-g-400">
              <ElIcon :size="48" class="mb-3"><ChatDotRound /></ElIcon>
              <p class="text-sm">开始一段新的对话吧</p>
            </div>
          </template>

          <template v-for="(msg, idx) in messages" :key="idx">
            <!-- Tool call card -->
            <div v-if="msg.role === 'tool_call'" class="mb-4 flex w-full items-start gap-2.5">
              <div
                class="flex size-8 shrink-0 items-center justify-center rounded-full bg-amber-500 text-xs font-bold text-white"
              >
                <ElIcon :size="16"><SetUp /></ElIcon>
              </div>
              <div class="max-w-[80%]">
                <div
                  class="inline-block rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-sm"
                >
                  <div class="mb-1 flex items-center gap-1.5 font-medium text-amber-700">
                    <ElIcon :size="14"><SetUp /></ElIcon>
                    <span>工具调用: {{ msg.toolName }}</span>
                  </div>
                  <pre
                    class="mt-1 max-h-32 overflow-auto rounded bg-amber-100/60 p-2 text-xs text-g-700"
                    >{{ msg.toolArgs }}</pre
                  >
                </div>
              </div>
            </div>

            <!-- Tool result card -->
            <div
              v-else-if="msg.role === 'tool_result'"
              class="mb-4 flex w-full items-start gap-2.5"
            >
              <div
                class="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-xs font-bold text-white"
              >
                <ElIcon :size="16"><Check /></ElIcon>
              </div>
              <div class="max-w-[80%]">
                <div
                  class="inline-block rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm"
                >
                  <div
                    class="flex cursor-pointer items-center gap-1.5 font-medium text-emerald-700"
                    @click="msg.collapsed = !msg.collapsed"
                  >
                    <ElIcon :size="14"><Check /></ElIcon>
                    <span>工具结果</span>
                    <ElIcon :size="12" class="ml-1">
                      <component :is="msg.collapsed ? ArrowDown : ArrowUp" />
                    </ElIcon>
                  </div>
                  <pre
                    v-show="!msg.collapsed"
                    class="mt-1 max-h-40 overflow-auto rounded bg-emerald-100/60 p-2 text-xs text-g-700"
                    >{{ msg.content }}</pre
                  >
                </div>
              </div>
            </div>

            <!-- User / Assistant messages -->
            <div
              v-else
              :class="[
                'mb-5 flex w-full items-start gap-2.5',
                msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
              ]"
            >
              <div
                class="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                :class="msg.role === 'user' ? 'bg-theme' : 'bg-g-600'"
              >
                {{ msg.role === 'user' ? 'U' : 'AI' }}
              </div>
              <div :class="['max-w-[80%]', msg.role === 'user' ? 'text-right' : 'text-left']">
                <!-- User message: plain text with inline images -->
                <div
                  v-if="msg.role === 'user'"
                  class="inline-block whitespace-pre-wrap rounded-lg bg-theme/15 px-3.5 py-2.5 text-sm leading-relaxed text-g-900"
                >
                  <template v-for="(part, pi) in parseUserContent(msg.content)" :key="pi">
                    <img
                      v-if="part.type === 'image'"
                      :src="part.value"
                      class="my-1 inline-block max-w-[200px] rounded-lg"
                      alt="uploaded image"
                    />
                    <span v-else>{{ part.value }}</span>
                  </template>
                </div>

                <!-- Assistant message: rendered Markdown -->
                <div v-else>
                  <div
                    class="art-markdown inline-block rounded-lg bg-g-200/60 px-3.5 py-2.5 text-sm leading-relaxed text-g-900"
                    v-html="renderMarkdown(msg.content)"
                  />
                  <span
                    v-if="isStreaming && idx === messages.length - 1 && msg.role === 'assistant'"
                    class="animate-pulse"
                    >▌</span
                  >
                  <!-- RAG Citations -->
                  <div
                    v-if="msg.citations && msg.citations.length > 0"
                    class="mt-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2"
                  >
                    <div class="mb-1.5 text-xs font-medium text-blue-700">参考来源</div>
                    <div
                      v-for="(cite, ci) in msg.citations"
                      :key="ci"
                      class="mb-1 flex items-start gap-2 text-xs text-g-600"
                    >
                      <ElTag size="small" type="info" class="shrink-0">
                        {{ (cite.relevance_score * 100).toFixed(0) }}%
                      </ElTag>
                      <div>
                        <div class="font-medium">{{ cite.document_name }}</div>
                        <div class="mt-0.5 text-g-400">{{ cite.snippet }}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- ─── 输入区域 ─── -->
        <div class="border-t-d px-4 py-3">
          <!-- Image preview -->
          <div v-if="pendingImages.length > 0" class="mb-2 flex flex-wrap gap-2">
            <div v-for="(img, i) in pendingImages" :key="i" class="group relative inline-block">
              <img
                :src="img.url"
                class="h-16 max-w-[120px] rounded-lg object-cover"
                alt="preview"
              />
              <div
                class="absolute -right-1.5 -top-1.5 flex size-5 cursor-pointer items-center justify-center rounded-full bg-danger text-white opacity-0 transition-opacity group-hover:opacity-100"
                @click="pendingImages.splice(i, 1)"
              >
                <ElIcon :size="12"><Close /></ElIcon>
              </div>
            </div>
          </div>

          <div class="flex items-end gap-2">
            <!-- Agent toggle -->
            <ElTooltip content="Agent 模式" placement="top">
              <ElButton
                :type="enableAgent ? 'warning' : 'default'"
                size="small"
                circle
                @click="enableAgent = !enableAgent"
              >
                <ElIcon :size="16"><SetUp /></ElIcon>
              </ElButton>
            </ElTooltip>

            <!-- Image upload -->
            <ElTooltip content="上传图片" placement="top">
              <label class="cursor-pointer">
                <ElButton size="small" circle @click.prevent>
                  <ElIcon :size="16"><Picture /></ElIcon>
                </ElButton>
                <input type="file" class="hidden" accept="image/*" @change="handleImageUpload" />
              </label>
            </ElTooltip>

            <ElInput
              v-model="messageText"
              type="textarea"
              :rows="2"
              :autosize="{ minRows: 1, maxRows: 5 }"
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
              resize="none"
              :disabled="isStreaming"
              @keydown="handleKeydown"
              @paste="handlePaste"
            />
            <ElButton
              type="primary"
              :icon="isStreaming ? Loading : Promotion"
              :loading="isStreaming"
              :disabled="!canSend && !isStreaming"
              circle
              @click="isStreaming ? stopStream() : sendMessage()"
            />
          </div>
        </div>
      </div>
    </ElDrawer>

    <!-- Document preview dialog -->
    <ElDialog v-model="docPreviewVisible" title="文档预览" width="600px" destroy-on-close>
      <pre class="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded bg-g-100 p-4 text-sm">{{
        docPreviewContent
      }}</pre>
    </ElDialog>
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
    ChatDotRound,
    Picture,
    View,
    SetUp,
    Check
  } from '@element-plus/icons-vue'
  import { ElMessage } from 'element-plus'
  import { mittBus } from '@/utils/sys'
  import { marked } from 'marked'
  import hljs from 'highlight.js'
  import DOMPurify from 'dompurify'
  import 'highlight.js/styles/github-dark.css'
  import {
    fetchSessions,
    fetchCreateSession,
    fetchDeleteSession,
    fetchMessages,
    fetchDocuments,
    fetchUploadDocument,
    fetchDeleteDocument,
    fetchUploadImage,
    fetchProviders,
    fetchUpdateSession,
    streamChat,
    type ChatSession,
    type ChatDocument,
    type LLMProvider,
    type RagCitation
  } from '@/api/chat'

  defineOptions({ name: 'ArtChatWindow' })

  /* ─── Responsive ──────────────────────────────── */

  const MOBILE_BREAKPOINT = 640
  const { width } = useWindowSize()
  const isMobile = computed(() => width.value < MOBILE_BREAKPOINT)

  /* ─── UI State ────────────────────────────────── */

  const isDrawerVisible = ref(false)
  const messageText = ref('')
  const messageContainer = ref<HTMLElement | null>(null)
  const isStreaming = ref(false)
  let abortController: AbortController | null = null

  const showSessionList = ref(false)
  const showDocPanel = ref(false)
  const enableRag = ref(false)
  const enableAgent = ref(false)
  const showModelPicker = ref(false)

  /* ─── Data ────────────────────────────────────── */

  interface DisplayMessage {
    id: number
    role: 'user' | 'assistant' | 'system' | 'tool_call' | 'tool_result'
    content: string
    created_at: string
    toolName?: string
    toolArgs?: string
    collapsed?: boolean
    citations?: RagCitation[]
  }

  const sessions = ref<ChatSession[]>([])
  const activeSession = ref<ChatSession | null>(null)
  const messages = ref<DisplayMessage[]>([])
  const documents = ref<ChatDocument[]>([])
  const providers = ref<LLMProvider[]>([])
  const providersLoading = ref(false)

  /* ─── Image upload state ──────────────────────── */

  interface PendingImage {
    url: string
    marker: string
  }
  const pendingImages = ref<PendingImage[]>([])

  const canSend = computed(() => {
    return messageText.value.trim().length > 0 || pendingImages.value.length > 0
  })

  /* ─── Document preview state ──────────────────── */

  const docPreviewVisible = ref(false)
  const docPreviewContent = ref('')

  /* ─── Markdown rendering ──────────────────────── */

  const renderer = new marked.Renderer()
  renderer.code = function ({ text, lang }: { text: string; lang?: string; escaped?: boolean }) {
    const language = lang && hljs.getLanguage(lang) ? lang : ''
    const highlighted = language
      ? hljs.highlight(text, { language }).value
      : hljs.highlightAuto(text).value
    const langLabel = language || 'code'
    return `<pre><code class="hljs language-${langLabel}">${highlighted}</code></pre>`
  }

  marked.setOptions({
    renderer,
    breaks: true,
    gfm: true
  })

  function renderMarkdown(content: string): string {
    if (!content) return ''

    let processed = content.replace(/\[image:(\/api\/chat\/images\/[^\]]+)\]/g, '![]($1)')

    processed = processed.replace(
      /(https?:\/\/\S+\.(?:png|jpe?g|gif|webp|svg)(?:\?\S*)?)/gi,
      '![]($1)'
    )

    const rawHtml = marked.parse(processed) as string
    return DOMPurify.sanitize(rawHtml, {
      ADD_TAGS: ['img'],
      ADD_ATTR: ['src', 'alt', 'class']
    })
  }

  function parseUserContent(content: string): { type: 'text' | 'image'; value: string }[] {
    const parts: { type: 'text' | 'image'; value: string }[] = []
    const regex = /\[image:(\/api\/chat\/images\/[^\]]+)\]/g
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = regex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push({ type: 'text', value: content.slice(lastIndex, match.index) })
      }
      parts.push({ type: 'image', value: match[1] })
      lastIndex = regex.lastIndex
    }

    if (lastIndex < content.length) {
      parts.push({ type: 'text', value: content.slice(lastIndex) })
    }

    if (parts.length === 0) {
      parts.push({ type: 'text', value: content })
    }

    return parts
  }

  /* ─── Provider / Model switching ──────────────── */

  async function loadProviders() {
    if (providers.value.length > 0) return
    providersLoading.value = true
    try {
      providers.value = await fetchProviders()
    } catch {
      providers.value = []
    } finally {
      providersLoading.value = false
    }
  }

  async function selectModel(providerName: string, modelName: string) {
    if (!activeSession.value) return
    showModelPicker.value = false
    try {
      const updated = await fetchUpdateSession(activeSession.value.id, {
        model_provider: providerName,
        model_name: modelName
      })
      activeSession.value = updated
      const idx = sessions.value.findIndex((s) => s.id === updated.id)
      if (idx >= 0) sessions.value[idx] = updated
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '切换模型失败'
      ElMessage.error(msg)
    }
  }

  /* ─── Session management ──────────────────────── */

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
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '创建失败'
      ElMessage.error(msg)
    }
  }

  async function switchSession(s: ChatSession) {
    activeSession.value = s
    showSessionList.value = false
    try {
      const raw = await fetchMessages(s.id)
      messages.value = raw.map((m) => ({
        ...m,
        citations: undefined,
        collapsed: true
      })) as DisplayMessage[]
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
          const raw = await fetchMessages(activeSession.value.id)
          messages.value = raw.map((m) => ({
            ...m,
            citations: undefined,
            collapsed: true
          })) as DisplayMessage[]
        } else {
          messages.value = []
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '删除失败'
      ElMessage.error(msg)
    }
  }

  /* ─── Message sending ─────────────────────────── */

  async function sendMessage() {
    const text = messageText.value.trim()
    if (!text && pendingImages.value.length === 0) return
    if (isStreaming.value) return

    if (!activeSession.value) {
      await createNewSession()
      if (!activeSession.value) return
    }

    let fullContent = text
    for (const img of pendingImages.value) {
      fullContent += (fullContent ? '\n' : '') + img.marker
    }

    messages.value.push({
      id: 0,
      role: 'user',
      content: fullContent,
      created_at: ''
    })
    messageText.value = ''
    pendingImages.value = []
    scrollToBottom()

    messages.value.push({
      id: 0,
      role: 'assistant',
      content: '',
      created_at: '',
      citations: []
    })
    isStreaming.value = true

    const assistantIdx = messages.value.length - 1
    const docIds = enableRag.value
      ? documents.value.filter((d) => d.status === 'ready').map((d) => d.id)
      : []

    abortController = await streamChat(
      activeSession.value.id,
      {
        content: fullContent,
        enable_rag: enableRag.value && docIds.length > 0,
        document_ids: docIds,
        enable_agent: enableAgent.value || undefined
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
      },
      (type, data) => {
        if (type === 'tool_call') {
          messages.value.splice(assistantIdx, 0, {
            id: 0,
            role: 'tool_call',
            content: '',
            created_at: '',
            toolName: ((data as Record<string, unknown>).tool_name as string) || 'unknown',
            toolArgs: JSON.stringify((data as Record<string, unknown>).arguments ?? {}, null, 2),
            collapsed: false
          })
          scrollToBottom()
        } else if (type === 'tool_result') {
          messages.value.splice(assistantIdx, 0, {
            id: 0,
            role: 'tool_result',
            content:
              typeof (data as Record<string, unknown>).result === 'string'
                ? ((data as Record<string, unknown>).result as string)
                : JSON.stringify((data as Record<string, unknown>).result ?? '', null, 2),
            created_at: '',
            collapsed: true
          })
          scrollToBottom()
        } else if (type === 'rag_citations') {
          const citations = (data as Record<string, unknown>).citations as RagCitation[] | undefined
          if (citations && messages.value[assistantIdx]) {
            messages.value[assistantIdx].citations = citations
          }
        }
      }
    )
  }

  function stopStream() {
    abortController?.abort()
    isStreaming.value = false
  }

  function handleKeydown(e: Event | KeyboardEvent) {
    const ke = e as KeyboardEvent
    if (ke.key === 'Enter' && !ke.shiftKey) {
      ke.preventDefault()
      sendMessage()
    }
  }

  /* ─── Image handling ──────────────────────────── */

  async function handleImageUpload(e: Event) {
    const input = e.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    input.value = ''
    try {
      const result = await fetchUploadImage(file)
      pendingImages.value.push({
        url: result.url,
        marker: `[image:${result.url}]`
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '图片上传失败'
      ElMessage.error(msg)
    }
  }

  async function handlePaste(e: ClipboardEvent) {
    const items = e.clipboardData?.items
    if (!items) return
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (!file) continue
        try {
          const result = await fetchUploadImage(file)
          pendingImages.value.push({
            url: result.url,
            marker: `[image:${result.url}]`
          })
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : '图片上传失败'
          ElMessage.error(msg)
        }
        break
      }
    }
  }

  /* ─── Document management ─────────────────────── */

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
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '上传失败'
      ElMessage.error(msg)
    }
  }

  async function removeDocument(id: number) {
    try {
      await fetchDeleteDocument(id)
      documents.value = documents.value.filter((d) => d.id !== id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '删除失败'
      ElMessage.error(msg)
    }
  }

  function previewDocument(doc: ChatDocument) {
    const ext = doc.filename.split('.').pop()?.toLowerCase()
    if (ext === 'pdf') {
      window.open(`/api/chat/documents/${doc.id}/preview`, '_blank')
    } else if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext || '')) {
      window.open(`/api/chat/documents/${doc.id}/preview`, '_blank')
    } else {
      fetch(`/api/chat/documents/${doc.id}/preview`)
        .then((r) => r.text())
        .then((text) => {
          docPreviewContent.value = text
          docPreviewVisible.value = true
        })
        .catch(() => {
          ElMessage.error('预览失败')
        })
    }
  }

  /* ─── UI helpers ──────────────────────────────── */

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

<style scoped>
  /* Markdown content styling */
  :deep(.art-markdown) {
    line-height: 1.7;
  }

  :deep(.art-markdown h1),
  :deep(.art-markdown h2),
  :deep(.art-markdown h3),
  :deep(.art-markdown h4) {
    margin-top: 0.8em;
    margin-bottom: 0.4em;
    font-weight: 600;
  }

  :deep(.art-markdown h1) {
    font-size: 1.25em;
  }

  :deep(.art-markdown h2) {
    font-size: 1.15em;
  }

  :deep(.art-markdown h3) {
    font-size: 1.05em;
  }

  :deep(.art-markdown p) {
    margin: 0.4em 0;
  }

  :deep(.art-markdown ul),
  :deep(.art-markdown ol) {
    padding-left: 1.5em;
    margin: 0.4em 0;
  }

  :deep(.art-markdown li) {
    margin: 0.2em 0;
  }

  :deep(.art-markdown code) {
    padding: 0.15em 0.4em;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.06);
    font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
    font-size: 0.9em;
  }

  :deep(.art-markdown pre) {
    margin: 0.6em 0;
    border-radius: 8px;
    background: #1e1e2e !important;
    overflow-x: auto;
  }

  :deep(.art-markdown pre code) {
    display: block;
    padding: 1em;
    background: transparent;
    color: #cdd6f4;
    font-size: 0.85em;
    line-height: 1.6;
  }

  :deep(.art-markdown blockquote) {
    margin: 0.5em 0;
    padding: 0.3em 1em;
    border-left: 3px solid var(--el-color-primary);
    background: rgba(0, 0, 0, 0.03);
  }

  :deep(.art-markdown table) {
    width: 100%;
    margin: 0.5em 0;
    border-collapse: collapse;
  }

  :deep(.art-markdown th),
  :deep(.art-markdown td) {
    padding: 0.4em 0.8em;
    border: 1px solid #e0e0e0;
    text-align: left;
  }

  :deep(.art-markdown th) {
    background: rgba(0, 0, 0, 0.04);
    font-weight: 600;
  }

  :deep(.art-markdown img) {
    max-width: 200px;
    border-radius: 8px;
    margin: 0.3em 0;
  }

  :deep(.art-markdown a) {
    color: var(--el-color-primary);
    text-decoration: underline;
  }

  :deep(.art-markdown hr) {
    margin: 0.8em 0;
    border: none;
    border-top: 1px solid #e0e0e0;
  }
</style>
