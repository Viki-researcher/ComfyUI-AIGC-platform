<template>
  <div class="platform-dashboard" style="padding: 12px; overflow-y: auto">
    <!-- 仪表盘区域 -->
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">仪表盘</div>
          <div class="text-sm text-gray-500">全局概览：生成量、活跃项目、在线服务</div>
        </div>
        <ElButton @click="loadAll" :loading="loading" v-ripple>刷新</ElButton>
      </div>
    </ElCard>

    <!-- 核心指标卡片 -->
    <ElRow :gutter="12" class="mb-3">
      <ElCol :xs="12" :sm="6">
        <ElCard shadow="never" class="stat-card stat-blue">
          <div class="stat-value">{{ data.today_count }}</div>
          <div class="stat-label">今日生成量</div>
          <div class="stat-sub" v-if="data.yesterday_count">
            昨日 {{ data.yesterday_count }}
          </div>
        </ElCard>
      </ElCol>
      <ElCol :xs="12" :sm="6">
        <ElCard shadow="never" class="stat-card stat-green">
          <div class="stat-value">{{ data.active_projects }}</div>
          <div class="stat-label">活跃项目数</div>
        </ElCard>
      </ElCol>
      <ElCol :xs="12" :sm="6">
        <ElCard shadow="never" class="stat-card stat-purple">
          <div class="stat-value">{{ data.total_users }}</div>
          <div class="stat-label">平台用户数</div>
        </ElCard>
      </ElCol>
      <ElCol :xs="12" :sm="6">
        <ElCard shadow="never" class="stat-card stat-orange">
          <div class="stat-value">{{ data.success_rate }}%</div>
          <div class="stat-label">生成成功率</div>
          <div class="stat-sub">{{ data.success_count }} / {{ data.total_count }}</div>
        </ElCard>
      </ElCol>
    </ElRow>

    <!-- 在线服务状态 -->
    <ElCard shadow="never" class="mb-3">
      <template #header>
        <div class="font-semibold">在线服务</div>
      </template>
      <ElRow :gutter="12">
        <ElCol :span="12">
          <div class="service-item">
            <span class="status-dot" :class="data.online_comfy > 0 ? 'status-online' : 'status-stopped'"></span>
            <span>ComfyUI 实例</span>
            <ElTag :type="data.online_comfy > 0 ? 'success' : 'info'" size="small">
              {{ data.online_comfy }} 在线
            </ElTag>
          </div>
        </ElCol>
        <ElCol :span="12">
          <div class="service-item">
            <span class="status-dot" :class="data.online_annotation > 0 ? 'status-online' : 'status-stopped'"></span>
            <span>标注工具实例</span>
            <ElTag :type="data.online_annotation > 0 ? 'success' : 'info'" size="small">
              {{ data.online_annotation }} 在线
            </ElTag>
          </div>
        </ElCol>
      </ElRow>
    </ElCard>

    <!-- 数据统计区域 -->
    <ElCard class="mb-3" shadow="never">
      <div>
        <div class="text-lg font-semibold">数据统计</div>
        <div class="text-sm text-gray-500">按天/项目/用户聚合生成次数，支持曲线图展示</div>
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
        :loading="statsLoading"
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
          <ElTable :data="projectTableData" v-loading="statsLoading" height="260">
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
          <ElTable :data="userTableData" v-loading="statsLoading" height="260">
            <ElTableColumn prop="key" label="用户" />
            <ElTableColumn prop="count" label="次数" width="100" />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
  import { fetchDashboard } from '@/api/dashboard'
  import { fetchGetStats, fetchGetStatsTrend } from '@/api/stats'
  import type { LineDataItem } from '@/types/component/chart'

  defineOptions({ name: 'PlatformDashboard' })

  const loading = ref(false)
  const statsLoading = ref(false)
  const trendLoading = ref(false)

  const data = ref<Api.DataGen.DashboardOverview>({
    today_count: 0,
    yesterday_count: 0,
    total_count: 0,
    success_count: 0,
    success_rate: 0,
    active_projects: 0,
    total_users: 0,
    online_comfy: 0,
    online_annotation: 0
  })

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

  const _loadDashboard = async () => {
    data.value = await fetchDashboard()
  }

  const loadDashboard = async () => {
    loading.value = true
    try {
      await _loadDashboard()
    } finally {
      loading.value = false
    }
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

  const _loadStats = async () => {
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
  }

  const loadStats = async () => {
    statsLoading.value = true
    trendLoading.value = true
    try {
      await _loadStats()
    } finally {
      statsLoading.value = false
      trendLoading.value = false
    }
  }

  const loadAll = async () => {
    loading.value = true
    statsLoading.value = true
    trendLoading.value = true
    try {
      await Promise.all([_loadDashboard(), _loadStats()])
    } finally {
      loading.value = false
      statsLoading.value = false
      trendLoading.value = false
    }
  }

  const handleReset = () => {
    filters.value = { start_date: undefined, end_date: undefined }
    loadAll()
  }

  onMounted(loadAll)

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
  .stat-card {
    text-align: center;
    padding: 8px 0;
  }

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.2;
  }

  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
  }

  .stat-sub {
    font-size: 11px;
    color: #c0c4cc;
    margin-top: 2px;
  }

  .stat-blue .stat-value {
    color: #409eff;
  }

  .stat-green .stat-value {
    color: #67c23a;
  }

  .stat-purple .stat-value {
    color: #9b59b6;
  }

  .stat-orange .stat-value {
    color: #e6a23c;
  }

  .service-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
    font-size: 14px;
  }

  .status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .status-online {
    background-color: #67c23a;
    box-shadow: 0 0 4px #67c23a;
  }

  .status-stopped {
    background-color: #c0c4cc;
  }

  .platform-dashboard > :deep(.el-card) {
    flex-shrink: 0;
  }
</style>
