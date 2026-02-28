<template>
  <div class="platform-stats art-full-height">
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">数据统计</div>
          <div class="text-sm text-gray-500">按天/项目/用户聚合生成次数，支持曲线图展示</div>
        </div>
        <ElButton @click="loadAll" :loading="loading" v-ripple>刷新</ElButton>
      </div>
    </ElCard>

    <ElCard class="mb-3" shadow="never">
      <ArtSearchBar
        v-model="filters"
        :items="filterItems"
        :showExpand="false"
        @search="loadAll"
        @reset="handleReset"
      />
    </ElCard>

    <!-- 按天趋势 -->
    <ElCard class="mb-3" shadow="never">
      <template #header>
        <div class="font-semibold">每日生成趋势</div>
      </template>
      <ArtLineChart
        v-if="dayXAxis.length"
        :loading="loading"
        :xAxisData="dayXAxis"
        :data="daySeries"
        height="280px"
        :showAreaColor="true"
      />
      <ElEmpty v-else description="暂无数据" />
    </ElCard>

    <ElRow :gutter="12" class="mb-3">
      <ElCol :xs="24" :md="12">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">按项目趋势曲线</div>
          </template>
          <ArtLineChart
            v-if="projectTrend.dates.length"
            :loading="trendLoading"
            :xAxisData="projectTrend.dates"
            :data="projectTrendSeries"
            height="300px"
            :showAreaColor="true"
            :showLegend="true"
            legendPosition="bottom"
          />
          <ElEmpty v-else description="暂无数据" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :md="12">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">按用户趋势曲线</div>
          </template>
          <ArtLineChart
            v-if="userTrend.dates.length"
            :loading="trendLoading"
            :xAxisData="userTrend.dates"
            :data="userTrendSeries"
            height="300px"
            :showAreaColor="true"
            :showLegend="true"
            legendPosition="bottom"
          />
          <ElEmpty v-else description="暂无数据" />
        </ElCard>
      </ElCol>
    </ElRow>

    <ElRow :gutter="12">
      <ElCol :xs="24" :md="12">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">按项目统计</div>
          </template>
          <ElTable :data="projectTableData" v-loading="loading" height="260">
            <ElTableColumn prop="key" label="项目" />
            <ElTableColumn prop="count" label="次数" width="100" />
          </ElTable>
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :md="12">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">按用户统计</div>
          </template>
          <ElTable :data="userTableData" v-loading="loading" height="260">
            <ElTableColumn prop="key" label="用户" />
            <ElTableColumn prop="count" label="次数" width="100" />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
  import { fetchGetStats, fetchGetStatsTrend } from '@/api/stats'
  import type { LineDataItem } from '@/types/component/chart'

  defineOptions({ name: 'PlatformStats' })

  const loading = ref(false)
  const trendLoading = ref(false)

  const filters = ref<Record<string, any>>({
    start_date: undefined,
    end_date: undefined
  })

  const filterItems = computed(() => [
    {
      key: 'start_date',
      label: '开始日期',
      type: 'date',
      props: { type: 'date', placeholder: '选择开始日期', valueFormat: 'YYYY-MM-DD' },
      span: 8
    },
    {
      key: 'end_date',
      label: '结束日期',
      type: 'date',
      props: { type: 'date', placeholder: '选择结束日期', valueFormat: 'YYYY-MM-DD' },
      span: 8
    }
  ])

  function formatDate(val: any): string | undefined {
    if (!val) return undefined
    if (typeof val === 'string') return val.slice(0, 10)
    if (val instanceof Date) {
      const y = val.getFullYear()
      const m = String(val.getMonth() + 1).padStart(2, '0')
      const d = String(val.getDate()).padStart(2, '0')
      return `${y}-${m}-${d}`
    }
    return undefined
  }

  const dayRaw = ref<any[]>([])
  const projectRaw = ref<any[]>([])
  const userRaw = ref<any[]>([])
  const projectTrend = ref<{ dates: string[]; series: { name: string; data: number[] }[] }>({
    dates: [],
    series: []
  })
  const userTrend = ref<{ dates: string[]; series: { name: string; data: number[] }[] }>({
    dates: [],
    series: []
  })

  const loadAll = async () => {
    loading.value = true
    trendLoading.value = true
    try {
      const params = {
        start_date: formatDate(filters.value.start_date),
        end_date: formatDate(filters.value.end_date)
      }
      const [dayData, projectData, userData, projTrend, usrTrend] = await Promise.all([
        fetchGetStats({ dimension: 'day', ...params }),
        fetchGetStats({ dimension: 'project', ...params }),
        fetchGetStats({ dimension: 'user', ...params }),
        fetchGetStatsTrend({ group_by: 'project', ...params }),
        fetchGetStatsTrend({ group_by: 'user', ...params })
      ])
      dayRaw.value = dayData || []
      projectRaw.value = projectData || []
      userRaw.value = userData || []
      projectTrend.value = projTrend || { dates: [], series: [] }
      userTrend.value = usrTrend || { dates: [], series: [] }
    } finally {
      loading.value = false
      trendLoading.value = false
    }
  }

  onMounted(loadAll)

  const handleReset = () => {
    filters.value = { start_date: undefined, end_date: undefined }
    loadAll()
  }

  const dayXAxis = computed(() => (dayRaw.value || []).map((i: any) => i.date))
  const daySeries = computed(() => (dayRaw.value || []).map((i: any) => i.count))

  const projectTableData = computed(() =>
    (projectRaw.value || []).map((i: any) => ({
      key: i.project_name || `项目 ${i.project_id}`,
      count: i.count
    }))
  )

  const userTableData = computed(() =>
    (userRaw.value || []).map((i: any) => ({
      key: i.user_name || `用户 ${i.user_id}`,
      count: i.count
    }))
  )

  const projectTrendSeries = computed<LineDataItem[]>(() =>
    (projectTrend.value.series || []).map((s) => ({
      name: s.name,
      data: s.data,
      showAreaColor: true
    }))
  )

  const userTrendSeries = computed<LineDataItem[]>(() =>
    (userTrend.value.series || []).map((s) => ({
      name: s.name,
      data: s.data,
      showAreaColor: true
    }))
  )
</script>

<style scoped>
  .platform-stats {
    padding: 12px;
    overflow-y: auto;
  }

  .platform-stats > :deep(.el-card) {
    flex-shrink: 0;
  }
</style>
