<template>
  <div class="workflow-editor art-full-height">
    <!-- Top Bar -->
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">工作流编辑器</div>
          <div class="text-sm text-gray-500">ComfyUI 工作流可视化编辑、AI 生成与提交</div>
        </div>
        <div class="flex gap-2">
          <ElButton @click="showTemplatePanel = !showTemplatePanel" v-ripple>
            {{ showTemplatePanel ? '隐藏模板' : '模板库' }}
          </ElButton>
          <ElButton type="success" @click="openAiDialog" v-ripple>AI 生成</ElButton>
          <ElButton
            type="primary"
            @click="handleSubmit"
            :loading="submitting"
            :disabled="!workflowJson"
            v-ripple
          >
            提交到 ComfyUI
          </ElButton>
        </div>
      </div>
    </ElCard>

    <div class="editor-body">
      <!-- Left Panel - Template Library -->
      <div v-if="showTemplatePanel" class="template-panel">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">模板库</div>
          </template>
          <div class="template-list">
            <ElCard
              v-for="tpl in templates"
              :key="tpl.name"
              shadow="hover"
              class="template-card mb-3 cursor-pointer"
              @click="loadTemplate(tpl)"
            >
              <div class="font-semibold text-sm">{{ tpl.display_name }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ tpl.description }}</div>
            </ElCard>
            <ElEmpty v-if="templates.length === 0" description="暂无模板" :image-size="60" />
          </div>
        </ElCard>
      </div>

      <!-- Center Panel - JSON Editor -->
      <div class="json-panel">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="flex-cb">
              <span class="font-semibold">工作流 JSON</span>
              <div class="flex gap-2">
                <ElButton size="small" @click="formatJson" v-ripple>格式化</ElButton>
                <ElButton size="small" @click="parseParams" v-ripple>解析参数</ElButton>
              </div>
            </div>
          </template>
          <ElInput
            v-model="workflowJson"
            type="textarea"
            :autosize="{ minRows: 20, maxRows: 40 }"
            placeholder='粘贴或生成 ComfyUI 工作流 JSON...'
            class="json-textarea"
            @change="parseParams"
          />
        </ElCard>
      </div>

      <!-- Right Panel - Parameters -->
      <div class="params-panel">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">参数面板</div>
          </template>
          <ElForm label-position="top" size="default" class="params-form">
            <ElFormItem label="正向提示词">
              <ElInput
                v-model="params.prompt"
                type="textarea"
                :rows="3"
                placeholder="描述你想要的图像内容"
                @change="syncParamsToJson"
              />
            </ElFormItem>

            <ElFormItem label="反向提示词">
              <ElInput
                v-model="params.negativePrompt"
                type="textarea"
                :rows="2"
                placeholder="描述你不想要的内容"
                @change="syncParamsToJson"
              />
            </ElFormItem>

            <ElFormItem label="宽度">
              <ElInputNumber
                v-model="params.width"
                :min="64"
                :max="4096"
                :step="64"
                @change="syncParamsToJson"
              />
            </ElFormItem>

            <ElFormItem label="高度">
              <ElInputNumber
                v-model="params.height"
                :min="64"
                :max="4096"
                :step="64"
                @change="syncParamsToJson"
              />
            </ElFormItem>

            <ElFormItem label="采样步数">
              <ElSlider
                v-model="params.steps"
                :min="1"
                :max="100"
                show-input
                @change="syncParamsToJson"
              />
            </ElFormItem>

            <ElFormItem label="CFG Scale">
              <ElSlider
                v-model="params.cfgScale"
                :min="1"
                :max="30"
                :step="0.5"
                show-input
                @change="syncParamsToJson"
              />
            </ElFormItem>

            <ElFormItem label="种子">
              <div class="flex gap-2 w-full">
                <ElInputNumber
                  v-model="params.seed"
                  :min="0"
                  :max="999999999"
                  class="flex-1"
                  @change="syncParamsToJson"
                />
                <ElButton @click="randomSeed" v-ripple>随机</ElButton>
              </div>
            </ElFormItem>

            <ElFormItem label="采样器">
              <ElSelect v-model="params.samplerName" class="w-full" @change="syncParamsToJson">
                <ElOption
                  v-for="s in samplerOptions"
                  :key="s"
                  :label="s"
                  :value="s"
                />
              </ElSelect>
            </ElFormItem>
          </ElForm>
        </ElCard>
      </div>
    </div>

    <!-- AI Assist Dialog -->
    <ElDialog v-model="aiDialogVisible" title="AI 工作流生成" width="600px" append-to-body>
      <ElForm label-position="top">
        <ElFormItem label="描述你想要的工作流">
          <ElInput
            v-model="aiDescription"
            type="textarea"
            :rows="4"
            placeholder="例如：生成一张 1024x1024 的风景画，使用 30 步采样，euler 采样器"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="aiDialogVisible = false" v-ripple>取消</ElButton>
          <ElButton
            type="primary"
            :loading="generating"
            :disabled="!aiDescription.trim()"
            @click="handleAiGenerate"
            v-ripple
          >
            生成工作流
          </ElButton>
        </div>
      </template>
    </ElDialog>

    <!-- Submit Dialog -->
    <ElDialog v-model="submitDialogVisible" title="提交工作流" width="480px" append-to-body>
      <ElForm label-position="top">
        <ElFormItem label="ComfyUI 实例地址">
          <ElInput v-model="comfyUrl" placeholder="例如: http://127.0.0.1:8200" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="submitDialogVisible = false" v-ripple>取消</ElButton>
          <ElButton
            type="primary"
            :loading="submitting"
            :disabled="!comfyUrl.trim()"
            @click="doSubmit"
            v-ripple
          >
            确认提交
          </ElButton>
        </div>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
  import { ElMessage } from 'element-plus'
  import {
    fetchWorkflowTemplates,
    fetchGenerateWorkflow,
    fetchSubmitWorkflow,
    type WorkflowTemplate
  } from '@/api/workflow'

  defineOptions({ name: 'PlatformWorkflow' })

  const showTemplatePanel = ref(true)
  const templates = ref<WorkflowTemplate[]>([])
  const workflowJson = ref('')
  const aiDialogVisible = ref(false)
  const aiDescription = ref('')
  const generating = ref(false)
  const submitDialogVisible = ref(false)
  const submitting = ref(false)
  const comfyUrl = ref('http://127.0.0.1:8200')

  const samplerOptions = [
    'euler',
    'euler_ancestral',
    'heun',
    'dpm_2',
    'dpm_2_ancestral',
    'lms',
    'dpm_fast',
    'dpm_adaptive',
    'dpmpp_2s_ancestral',
    'dpmpp_sde',
    'dpmpp_2m',
    'ddim',
    'uni_pc'
  ]

  const params = ref({
    prompt: '',
    negativePrompt: '',
    width: 512,
    height: 512,
    steps: 20,
    cfgScale: 7,
    seed: 42,
    samplerName: 'euler_ancestral'
  })

  const loadTemplates = async () => {
    try {
      templates.value = await fetchWorkflowTemplates()
    } catch {
      ElMessage.warning('模板加载失败')
    }
  }

  const loadTemplate = (tpl: WorkflowTemplate) => {
    workflowJson.value = JSON.stringify(tpl.workflow, null, 2)
    parseParams()
    ElMessage.success(`已加载模板: ${tpl.display_name}`)
  }

  const formatJson = () => {
    try {
      const obj = JSON.parse(workflowJson.value)
      workflowJson.value = JSON.stringify(obj, null, 2)
    } catch {
      ElMessage.error('JSON 格式无效')
    }
  }

  const parseParams = () => {
    try {
      const wf = JSON.parse(workflowJson.value)
      for (const node of Object.values(wf) as any[]) {
        if (node.class_type === 'KSampler' && node.inputs) {
          params.value.steps = node.inputs.steps ?? params.value.steps
          params.value.cfgScale = node.inputs.cfg ?? params.value.cfgScale
          params.value.seed = node.inputs.seed ?? params.value.seed
          params.value.samplerName = node.inputs.sampler_name ?? params.value.samplerName
        }
        if (node.class_type === 'EmptyLatentImage' && node.inputs) {
          params.value.width = node.inputs.width ?? params.value.width
          params.value.height = node.inputs.height ?? params.value.height
        }
        if (node.class_type === 'CLIPTextEncode' && node.inputs?.text) {
          const samplerNode = Object.values(wf).find(
            (n: any) => n.class_type === 'KSampler'
          ) as any
          if (samplerNode?.inputs) {
            const positiveRef = samplerNode.inputs.positive
            const negativeRef = samplerNode.inputs.negative
            const nodeId = Object.entries(wf).find(([, v]) => v === node)?.[0]
            if (positiveRef && Array.isArray(positiveRef) && positiveRef[0] === nodeId) {
              params.value.prompt = node.inputs.text
            }
            if (negativeRef && Array.isArray(negativeRef) && negativeRef[0] === nodeId) {
              params.value.negativePrompt = node.inputs.text
            }
          }
        }
      }
    } catch {
      // not valid JSON yet
    }
  }

  const syncParamsToJson = () => {
    try {
      const wf = JSON.parse(workflowJson.value)
      for (const node of Object.values(wf) as any[]) {
        if (node.class_type === 'KSampler' && node.inputs) {
          node.inputs.steps = params.value.steps
          node.inputs.cfg = params.value.cfgScale
          node.inputs.seed = params.value.seed
          node.inputs.sampler_name = params.value.samplerName
        }
        if (node.class_type === 'EmptyLatentImage' && node.inputs) {
          node.inputs.width = params.value.width
          node.inputs.height = params.value.height
        }
      }

      const samplerNode = Object.values(wf).find((n: any) => n.class_type === 'KSampler') as any
      if (samplerNode?.inputs) {
        const positiveRef = samplerNode.inputs.positive
        const negativeRef = samplerNode.inputs.negative
        if (positiveRef && Array.isArray(positiveRef)) {
          const pNode = wf[positiveRef[0]]
          if (pNode?.class_type === 'CLIPTextEncode' && pNode.inputs) {
            pNode.inputs.text = params.value.prompt
          }
        }
        if (negativeRef && Array.isArray(negativeRef)) {
          const nNode = wf[negativeRef[0]]
          if (nNode?.class_type === 'CLIPTextEncode' && nNode.inputs) {
            nNode.inputs.text = params.value.negativePrompt
          }
        }
      }

      workflowJson.value = JSON.stringify(wf, null, 2)
    } catch {
      // JSON not valid, skip sync
    }
  }

  const randomSeed = () => {
    params.value.seed = Math.floor(Math.random() * 999999999)
    syncParamsToJson()
  }

  const openAiDialog = () => {
    aiDescription.value = ''
    aiDialogVisible.value = true
  }

  const handleAiGenerate = async () => {
    generating.value = true
    try {
      const result = await fetchGenerateWorkflow(aiDescription.value)
      workflowJson.value = JSON.stringify(result.workflow, null, 2)
      parseParams()
      aiDialogVisible.value = false
      ElMessage.success('工作流生成成功')
    } catch {
      ElMessage.error('AI 生成失败，请重试')
    } finally {
      generating.value = false
    }
  }

  const handleSubmit = () => {
    submitDialogVisible.value = true
  }

  const doSubmit = async () => {
    submitting.value = true
    try {
      const wf = JSON.parse(workflowJson.value)
      const result = await fetchSubmitWorkflow(wf, comfyUrl.value)
      submitDialogVisible.value = false
      ElMessage.success(`工作流已提交，Prompt ID: ${result.prompt_id}`)
    } catch {
      ElMessage.error('提交失败，请检查 ComfyUI 地址是否正确')
    } finally {
      submitting.value = false
    }
  }

  onMounted(loadTemplates)
</script>

<style scoped>
  .workflow-editor {
    padding: 12px;
  }

  .editor-body {
    display: flex;
    gap: 12px;
    height: calc(100vh - 180px);
    min-height: 500px;
  }

  .template-panel {
    width: 240px;
    min-width: 200px;
    flex-shrink: 0;
  }

  .template-list {
    max-height: calc(100vh - 280px);
    overflow-y: auto;
  }

  .template-card:hover {
    border-color: var(--el-color-primary);
  }

  .json-panel {
    flex: 1;
    min-width: 300px;
  }

  .params-panel {
    width: 320px;
    min-width: 280px;
    flex-shrink: 0;
    overflow-y: auto;
  }

  .params-form {
    max-height: calc(100vh - 280px);
    overflow-y: auto;
    padding-right: 8px;
  }

  .json-textarea :deep(.el-textarea__inner) {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    line-height: 1.5;
  }

  .h-full {
    height: 100%;
  }

  @media (max-width: 768px) {
    .editor-body {
      flex-direction: column;
      height: auto;
    }

    .template-panel,
    .params-panel {
      width: 100%;
      min-width: unset;
    }

    .template-list,
    .params-form {
      max-height: 300px;
    }
  }
</style>
