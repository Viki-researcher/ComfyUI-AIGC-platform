<template>
  <div class="platform-dashboard" style="padding: 12px; overflow-y: auto">
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">仪表盘</div>
          <div class="text-sm text-gray-500">全局概览：生成量、活跃项目、在线服务</div>
        </div>
        <ElButton @click="loadData" :loading="loading" v-ripple>刷新</ElButton>
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
  </div>
</template>

<script setup lang="ts">
  import { fetchDashboard } from '@/api/dashboard'

  defineOptions({ name: 'PlatformDashboard' })

  const loading = ref(false)
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

  const loadData = async () => {
    loading.value = true
    try {
      data.value = await fetchDashboard()
    } finally {
      loading.value = false
    }
  }

  onMounted(loadData)
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
</style>
