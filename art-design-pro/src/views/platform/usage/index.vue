<template>
  <div class="platform-usage art-full-height">
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">用量与计费</div>
          <div class="text-sm text-gray-500">Token 用量统计、对话数、文档数</div>
        </div>
        <ElButton @click="loadAll" :loading="loading" v-ripple>刷新</ElButton>
      </div>
    </ElCard>

    <!-- Overview cards -->
    <ElRow :gutter="12" class="mb-3">
      <ElCol :xs="24" :sm="8">
        <ElCard shadow="hover">
          <ElStatistic title="总 Token 用量" :value="overview.totalTokens" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :sm="8">
        <ElCard shadow="hover">
          <ElStatistic title="总对话数" :value="overview.totalSessions" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :sm="8">
        <ElCard shadow="hover">
          <ElStatistic title="总文档数" :value="overview.totalDocuments" />
        </ElCard>
      </ElCol>
    </ElRow>

    <!-- Daily usage chart -->
    <ElCard class="mb-3" shadow="never">
      <template #header>
        <div class="font-semibold">每日 Token 用量趋势</div>
      </template>
      <div ref="chartRef" style="height: 320px" v-loading="loading"></div>
    </ElCard>

    <!-- Per-model breakdown -->
    <ElCard class="mb-3" shadow="never">
      <template #header>
        <div class="font-semibold">模型用量明细</div>
      </template>
      <ElTable :data="modelBreakdown" v-loading="loading" stripe>
        <ElTableColumn prop="provider" label="提供商" />
        <ElTableColumn prop="model" label="模型" />
        <ElTableColumn prop="prompt_tokens" label="Prompt Tokens" />
        <ElTableColumn prop="completion_tokens" label="Completion Tokens" />
        <ElTableColumn prop="total_tokens" label="总 Tokens" />
        <ElTableColumn prop="count" label="调用次数" />
      </ElTable>
    </ElCard>

    <!-- Admin view -->
    <ElCard v-if="isAdmin" shadow="never">
      <template #header>
        <div class="font-semibold">全部用户用量（管理员）</div>
      </template>
      <ElTable :data="allUsersData" v-loading="adminLoading" stripe>
        <ElTableColumn prop="user_id" label="用户 ID" width="100" />
        <ElTableColumn prop="total_prompt_tokens" label="Prompt Tokens" />
        <ElTableColumn prop="total_completion_tokens" label="Completion Tokens" />
        <ElTableColumn prop="total_tokens" label="总 Tokens" />
        <ElTableColumn prop="call_count" label="调用次数" width="100" />
      </ElTable>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { fetchUsage, fetchUsageAll, fetchSessions, fetchDocuments } from '@/api/chat'
  import { useUserStore } from '@/store/modules/user'
  import { echarts } from '@/plugins/echarts'

  defineOptions({ name: 'PlatformUsage' })

  const userStore = useUserStore()
  const isAdmin = computed(() => {
    const roles = userStore.getUserInfo.roles || []
    return roles.includes('R_SUPER')
  })

  const loading = ref(false)
  const adminLoading = ref(false)
  const chartRef = ref<HTMLElement>()

  const overview = ref({
    totalTokens: 0,
    totalSessions: 0,
    totalDocuments: 0
  })

  interface ModelRow {
    provider: string
    model: string
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
    count: number
  }

  const modelBreakdown = ref<ModelRow[]>([])
  const allUsersData = ref<Record<string, unknown>[]>([])

  let chartInstance: ReturnType<typeof echarts.init> | null = null

  const loadUsage = async () => {
    const data = (await fetchUsage()) as Record<string, unknown>
    overview.value.totalTokens = (data.total_tokens as number) || 0

    const byModel = (data.by_model as Record<string, Record<string, number>>) || {}
    modelBreakdown.value = Object.entries(byModel).map(([key, val]) => {
      const [provider, ...rest] = key.split('/')
      return {
        provider,
        model: rest.join('/'),
        prompt_tokens: val.prompt_tokens || 0,
        completion_tokens: val.completion_tokens || 0,
        total_tokens: (val.prompt_tokens || 0) + (val.completion_tokens || 0),
        count: val.count || 0
      }
    })
  }

  const loadSessions = async () => {
    const sessions = await fetchSessions()
    overview.value.totalSessions = sessions?.length || 0
  }

  const loadDocuments = async () => {
    const docs = await fetchDocuments()
    overview.value.totalDocuments = docs?.length || 0
  }

  const loadAdminData = async () => {
    if (!isAdmin.value) return
    adminLoading.value = true
    try {
      allUsersData.value = (await fetchUsageAll()) || []
    } catch {
      allUsersData.value = []
    } finally {
      adminLoading.value = false
    }
  }

  const renderChart = () => {
    if (!chartRef.value) return
    if (!chartInstance) {
      chartInstance = echarts.init(chartRef.value)
    }

    const rows = modelBreakdown.value
    const dateMap = new Map<string, number>()
    const today = new Date()
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      dateMap.set(key, 0)
    }

    const totalTokens = rows.reduce((sum, r) => sum + r.total_tokens, 0)
    const dates = [...dateMap.keys()]
    if (totalTokens > 0 && dates.length > 0) {
      const lastDate = dates[dates.length - 1]
      dateMap.set(lastDate, totalTokens)
    }

    chartInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 20, right: 20, bottom: 30, left: 60 },
      xAxis: {
        type: 'category',
        data: dates
      },
      yAxis: { type: 'value', name: 'Tokens' },
      series: [
        {
          data: dates.map((d) => dateMap.get(d) || 0),
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.15 }
        }
      ]
    })
  }

  const loadAll = async () => {
    loading.value = true
    try {
      await Promise.all([loadUsage(), loadSessions(), loadDocuments()])
      await nextTick()
      renderChart()
    } finally {
      loading.value = false
    }
    loadAdminData()
  }

  onMounted(loadAll)

  onBeforeUnmount(() => {
    chartInstance?.dispose()
  })
</script>

<style scoped>
  .platform-usage {
    padding: 12px;
  }
</style>
