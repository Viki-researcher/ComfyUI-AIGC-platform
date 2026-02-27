import request from '@/utils/http'

/* ─── Types ──────────────────────────────────────── */

export interface WorkflowTemplate {
  name: string
  display_name: string
  description: string
  workflow: Record<string, any>
}

export interface GenerateWorkflowResult {
  workflow: Record<string, any>
}

export interface SubmitWorkflowResult {
  prompt_id: string
  status: string
}

export interface ModifyWorkflowResult {
  workflow: Record<string, any>
}

/* ─── API ────────────────────────────────────────── */

export function fetchWorkflowTemplates() {
  return request.get<WorkflowTemplate[]>({ url: '/api/workflow/templates' })
}

export function fetchGenerateWorkflow(description: string) {
  return request.post<GenerateWorkflowResult>({
    url: '/api/workflow/generate',
    params: { description }
  })
}

export function fetchSubmitWorkflow(workflow: Record<string, any>, comfyUrl: string) {
  return request.post<SubmitWorkflowResult>({
    url: '/api/workflow/submit',
    params: { workflow, comfy_url: comfyUrl }
  })
}

export function fetchModifyWorkflow(workflow: Record<string, any>, modification: string) {
  return request.put<ModifyWorkflowResult>({
    url: '/api/workflow/modify',
    params: { workflow, modification }
  })
}
