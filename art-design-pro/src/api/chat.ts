import request from '@/utils/http'
import { useUserStore } from '@/store/modules/user'

/* ─── Types ──────────────────────────────────────── */

export interface LLMProvider {
  name: string
  display_name: string
  models: string[]
  default_model: string
}

export interface ChatSession {
  id: number
  title: string
  model_provider: string
  model_name: string
  system_prompt: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface ChatDocument {
  id: number
  filename: string
  file_size: number
  file_type: string
  chunk_count: number
  status: string
  created_at: string
}

export interface ChatSendParams {
  content: string
  model_provider?: string
  model_name?: string
  temperature?: number
  max_tokens?: number
  document_ids?: number[]
  enable_rag?: boolean
}

/* ─── Providers ──────────────────────────────────── */

export function fetchProviders() {
  return request.get<LLMProvider[]>({ url: '/api/chat/providers' })
}

/* ─── Sessions ───────────────────────────────────── */

export function fetchCreateSession(params: {
  title?: string
  model_provider?: string
  model_name?: string
  system_prompt?: string
}) {
  return request.post<ChatSession>({ url: '/api/chat/sessions', params })
}

export function fetchSessions() {
  return request.get<ChatSession[]>({ url: '/api/chat/sessions' })
}

export function fetchSession(sessionId: number) {
  return request.get<ChatSession>({ url: `/api/chat/sessions/${sessionId}` })
}

export function fetchUpdateSession(
  sessionId: number,
  params: { title?: string; model_provider?: string; model_name?: string; system_prompt?: string }
) {
  return request.put<ChatSession>({ url: `/api/chat/sessions/${sessionId}`, params })
}

export function fetchDeleteSession(sessionId: number) {
  return request.del<null>({ url: `/api/chat/sessions/${sessionId}` })
}

/* ─── Messages ───────────────────────────────────── */

export function fetchMessages(sessionId: number) {
  return request.get<ChatMessage[]>({ url: `/api/chat/sessions/${sessionId}/messages` })
}

/**
 * SSE 流式发送消息
 * 返回 ReadableStream reader，调用方逐段读取。
 */
export async function streamChat(
  sessionId: number,
  params: ChatSendParams,
  onToken: (text: string) => void,
  onDone: () => void,
  onError: (msg: string) => void
): Promise<AbortController> {
  const controller = new AbortController()
  const { accessToken } = useUserStore()

  try {
    const response = await fetch(`/api/chat/sessions/${sessionId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: accessToken || ''
      },
      body: JSON.stringify(params),
      signal: controller.signal
    })

    if (!response.ok || !response.body) {
      onError(`请求失败: HTTP ${response.status}`)
      return controller
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const processStream = async () => {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'token') {
              onToken(data.content)
            } else if (data.type === 'done') {
              onDone()
            } else if (data.type === 'error') {
              onError(data.content)
            }
          } catch {
            // skip malformed lines
          }
        }
      }
    }

    processStream().catch((err) => {
      if (err.name !== 'AbortError') {
        onError(String(err))
      }
    })
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      onError(String(err))
    }
  }

  return controller
}

/* ─── Documents ──────────────────────────────────── */

export function fetchDocuments() {
  return request.get<ChatDocument[]>({ url: '/api/chat/documents' })
}

export async function fetchUploadDocument(file: File): Promise<ChatDocument> {
  const formData = new FormData()
  formData.append('file', file)
  const { accessToken } = useUserStore()

  const response = await fetch('/api/chat/documents/upload', {
    method: 'POST',
    headers: { Authorization: accessToken || '' },
    body: formData
  })
  const json = await response.json()
  if (json.code !== 200) throw new Error(json.msg || '上传失败')
  return json.data
}

export function fetchDeleteDocument(docId: number) {
  return request.del<null>({ url: `/api/chat/documents/${docId}` })
}
