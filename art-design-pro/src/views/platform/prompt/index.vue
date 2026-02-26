<template>
  <div class="platform-prompt" style="padding: 12px; overflow-y: auto">
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">智能 Prompt 助手</div>
          <div class="text-sm text-gray-500">输入需求描述，生成高质量 ComfyUI Prompt</div>
        </div>
      </div>
    </ElCard>

    <ElRow :gutter="12">
      <ElCol :xs="24" :md="10">
        <ElCard shadow="never" class="mb-3">
          <template #header>
            <div class="font-semibold">需求输入</div>
          </template>
          <ElForm label-position="top">
            <ElFormItem label="需求描述">
              <ElInput
                v-model="form.description"
                type="textarea"
                :rows="4"
                placeholder="例如：一只白色的猫坐在窗台上，窗外是雨天的城市"
              />
            </ElFormItem>
            <ElFormItem label="风格模板">
              <ElSelect v-model="form.style" class="w-full">
                <ElOption
                  v-for="s in styles"
                  :key="s.key"
                  :label="s.key"
                  :value="s.key"
                />
              </ElSelect>
            </ElFormItem>
            <ElFormItem>
              <ElCheckbox v-model="form.enhance">添加质量增强词</ElCheckbox>
            </ElFormItem>
            <ElButton type="primary" :loading="generating" @click="handleGenerate" class="w-full" v-ripple>
              生成 Prompt
            </ElButton>
          </ElForm>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :md="14">
        <ElCard shadow="never" class="mb-3" v-if="result">
          <template #header>
            <div class="flex-cb">
              <div class="font-semibold">生成结果</div>
              <ElTag size="small">{{ result.style_used }}</ElTag>
            </div>
          </template>

          <div class="mb-3">
            <div class="flex-cb mb-1">
              <span class="text-sm font-medium text-green-600">正面提示词 (Positive)</span>
              <ElButton size="small" text @click="copyText(result.positive)">复制</ElButton>
            </div>
            <div class="prompt-box prompt-positive">{{ result.positive }}</div>
          </div>

          <div class="mb-3">
            <div class="flex-cb mb-1">
              <span class="text-sm font-medium text-red-500">反面提示词 (Negative)</span>
              <ElButton size="small" text @click="copyText(result.negative)">复制</ElButton>
            </div>
            <div class="prompt-box prompt-negative">{{ result.negative }}</div>
          </div>

          <div>
            <div class="text-sm font-medium text-gray-600 mb-1">提示</div>
            <ul class="text-xs text-gray-500 space-y-1">
              <li v-for="(tip, i) in result.tips" :key="i">· {{ tip }}</li>
            </ul>
          </div>
        </ElCard>

        <ElCard shadow="never" v-else>
          <ElEmpty description="输入需求描述并点击「生成 Prompt」" />
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
  import { fetchGeneratePrompt, fetchPromptStyles } from '@/api/prompt'
  import { ElMessage } from 'element-plus'

  defineOptions({ name: 'PlatformPrompt' })

  const generating = ref(false)
  const styles = ref<Api.DataGen.PromptStyle[]>([])
  const result = ref<Api.DataGen.PromptResponse | null>(null)

  const form = ref<Api.DataGen.PromptRequest>({
    description: '',
    style: '写实摄影',
    enhance: true
  })

  const loadStyles = async () => {
    try {
      styles.value = await fetchPromptStyles()
    } catch {
      /* ignore */
    }
  }

  onMounted(loadStyles)

  const handleGenerate = async () => {
    if (!form.value.description.trim()) {
      ElMessage.warning('请输入需求描述')
      return
    }
    generating.value = true
    try {
      result.value = await fetchGeneratePrompt(form.value)
    } catch (e: any) {
      ElMessage.error(e?.message || '生成失败')
    } finally {
      generating.value = false
    }
  }

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      ElMessage.success('已复制到剪贴板')
    })
  }
</script>

<style scoped>
  .prompt-box {
    padding: 12px;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.6;
    word-break: break-word;
    white-space: pre-wrap;
  }

  .prompt-positive {
    background: #f0f9eb;
    border: 1px solid #e1f3d8;
    color: #333;
  }

  .prompt-negative {
    background: #fef0f0;
    border: 1px solid #fde2e2;
    color: #333;
  }
</style>
