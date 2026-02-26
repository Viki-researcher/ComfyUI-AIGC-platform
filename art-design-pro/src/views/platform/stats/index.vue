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
        @reset="resetFilters"
      />
    </ElCard>

    <!-- 按天趋势 -->
    <ElCard class="mb-3" shadow="never">
      <template #header>
        <div class="font-semibold">每日生成趋势</div>
      </template>
      <ArtLineChart
        :loading="loading"
        :xAxisData="dayXAxis"
        :data="daySeries"
        height="280px"
        :showAreaColor="true"
      />
    </ElCard>

    <ElRow :gutter="12" class="mb-3">
      <!-- 按项目曲线 -->
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

      <!-- 按用户曲线 -->
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
      <!-- 按项目统计表 -->
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

      <!-- 按用户统计表 -->
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

  const filters = ref<{
    dimension: Api.DataGen.StatsDimension
    start_date?: string
    end_date?: string
  }>({
    dimension: 'day',
    start_date: undefined,
    end_date: undefined
  })

  const filterItems = computed(() => [
    {
      key: 'dimension',
      label: '维度',
      type: 'select',
      props: {
        placeholder: '请选择',
        options: [
          { label: '按天', value: 'day' },
          { label: '按项目', value: 'project' },
          { label: '按用户', value: 'user' }
        ]
      },
      span: 6
    },
    { key: 'start_date', label: '开始日期', type: 'date', props: { type: 'date' }, span: 6 },
    { key: 'end_date', label: '结束日期', type: 'date', props: { type: 'date' }, span: 6 }
  ])

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
        start_date: filters.value.start_date,
        end_date: filters.value.end_date
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

  const resetFilters = () => {
    filters.value = { dimension: 'day', start_date: undefined, end_date: undefined }
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
  }
</style>
