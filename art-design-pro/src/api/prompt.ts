import request from '@/utils/http'

export function fetchGeneratePrompt(params: Api.DataGen.PromptRequest) {
  return request.post<Api.DataGen.PromptResponse>({
    url: '/api/prompt/generate',
    params
  })
}

export function fetchPromptStyles() {
  return request.get<Api.DataGen.PromptStyle[]>({
    url: '/api/prompt/styles'
  })
}
