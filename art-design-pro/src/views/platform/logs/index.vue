<template>
  <div class="platform-logs art-full-height">
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">生成日志</div>
          <div class="text-sm text-gray-500">查看所有项目的数据生成记录</div>
        </div>
        <ElButton type="success" :loading="exporting" @click="handleExport" v-ripple>导出 Excel</ElButton>
      </div>
    </ElCard>

    <ElCard class="mb-3" shadow="never">
      <ElRow :gutter="12">
        <ElCol :xs="24" :sm="12" :md="4">
          <ElSelect
            v-model="searchForm.user_id"
            placeholder="选择用户"
            clearable
            filterable
            class="w-full"
            @change="handleSearch(searchForm)"
          >
            <ElOption
              v-for="u in userOptions"
              :key="u.value"
              :label="u.label"
              :value="u.value"
            />
          </ElSelect>
        </ElCol>
        <ElCol :xs="24" :sm="12" :md="4">
          <ElSelect
            v-model="searchForm.project_id"
            placeholder="选择项目"
            clearable
            filterable
            class="w-full"
            @change="handleSearch(searchForm)"
          >
            <ElOption
              v-for="p in projectOptions"
              :key="p.value"
              :label="p.label"
              :value="p.value"
            />
          </ElSelect>
        </ElCol>
        <ElCol :xs="24" :sm="12" :md="4">
          <ElSelect
            v-model="searchForm.status"
            placeholder="选择状态"
            clearable
            class="w-full"
            @change="handleSearch(searchForm)"
          >
            <ElOption label="成功" value="成功" />
            <ElOption label="失败" value="失败" />
            <ElOption label="未知" value="未知" />
          </ElSelect>
        </ElCol>
        <ElCol :xs="24" :sm="12" :md="4">
          <ElDatePicker
            v-model="searchForm.start"
            type="date"
            placeholder="开始日期"
            value-format="YYYY-MM-DD"
            class="w-full"
            @change="handleSearch(searchForm)"
          />
        </ElCol>
        <ElCol :xs="24" :sm="12" :md="4">
          <ElDatePicker
            v-model="searchForm.end"
            type="date"
            placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="w-full"
            @change="handleSearch(searchForm)"
          />
        </ElCol>
        <ElCol :xs="24" :sm="12" :md="4">
          <div class="flex gap-2">
            <ElButton type="primary" @click="handleSearch(searchForm)" v-ripple>搜索</ElButton>
            <ElButton @click="resetSearchForm" v-ripple>重置</ElButton>
          </div>
        </ElCol>
      </ElRow>
    </ElCard>

    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader :loading="loading" v-model:columns="columnChecks" @refresh="refreshData">
        <template #left>
          <div class="font-semibold">日志列表</div>
        </template>
      </ArtTableHeader>

      <ArtTable
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      />
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { useTable } from '@/hooks/core/useTable'
  import { fetchGetLogs, fetchExportLogs } from '@/api/logs'
  import { fetchGetProjects } from '@/api/projects'
  import { ElMessage } from 'element-plus'
  import type { ColumnOption } from '@/types/component'

  defineOptions({ name: 'PlatformLogs' })

  const searchForm = ref<Record<string, any>>({
    user_id: undefined,
    project_id: undefined,
    status: undefined,
    start: undefined,
    end: undefined
  })

  const projectOptions = ref<{ label: string; value: number }[]>([])
  const userOptions = ref<{ label: string; value: number }[]>([])

  const loadFilterOptions = async () => {
    try {
      const projects = await fetchGetProjects()
      projectOptions.value = (projects || []).map((p: any) => ({
        label: `${p.name} (${p.code})`,
        value: p.id
      }))
      const userMap = new Map<number, string>()
      ;(projects || []).forEach((p: any) => {
        if (p.owner_user_id && p.owner_user_name) {
          userMap.set(p.owner_user_id, p.owner_user_name)
        }
      })
      userOptions.value = Array.from(userMap.entries()).map(([id, name]) => ({
        label: name,
        value: id
      }))
    } catch {
      /* ignore */
    }
  }

  onMounted(loadFilterOptions)

  const columnsFactory = (): ColumnOption<Api.DataGen.LogListItem>[] => [
    { type: 'index', width: 60, label: '序号' },
    { prop: 'timestamp', label: '时间', width: 170, sortable: true },
    { prop: 'user', label: '用户', width: 140 },
    { prop: 'project', label: '项目', minWidth: 160 },
    { prop: 'status', label: '状态', width: 100 },
    { prop: 'concurrent_id', label: '并发ID', width: 120 },
    { prop: 'details', label: '详情', minWidth: 260 }
  ]

  const {
    columns,
    columnChecks,
    data,
    loading,
    pagination,
    getData,
    searchParams,
    resetSearchParams,
    handleSizeChange,
    handleCurrentChange,
    refreshData
  } = useTable({
    core: {
      apiFn: fetchGetLogs as any,
      apiParams: {
        current: 1,
        size: 20,
        ...searchForm.value
      },
      columnsFactory
    }
  })

  const handleSearch = (params: Record<string, any>) => {
    Object.assign(searchParams, params)
    getData()
  }

  const resetSearchForm = () => {
    searchForm.value = {
      user_id: undefined,
      project_id: undefined,
      status: undefined,
      start: undefined,
      end: undefined
    }
    resetSearchParams()
  }

  const exporting = ref(false)
  const handleExport = async () => {
    exporting.value = true
    try {
      await fetchExportLogs({
        user_id: searchForm.value.user_id,
        project_id: searchForm.value.project_id,
        status: searchForm.value.status,
        start: searchForm.value.start,
        end: searchForm.value.end
      })
      ElMessage.success('导出成功')
    } catch {
      ElMessage.error('导出失败，请重试')
    } finally {
      exporting.value = false
    }
  }
</script>

<style scoped>
  .platform-logs {
    padding: 12px;
  }
</style>
