<template>
  <div class="p-4">
    <ElCard shadow="never">
      <div class="text-lg font-semibold mb-2">审计日志</div>
      <ArtTable
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
      />
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import request from '@/utils/http'

  defineOptions({ name: 'SystemAuditLog' })

  const loading = ref(false)
  const tableData = ref<any[]>([])
  const pagination = ref({ current: 1, size: 20, total: 0 })

  const columns = [
    { prop: 'id', label: 'ID', width: 80 },
    { prop: 'username', label: '用户', width: 120 },
    { prop: 'method', label: '方法', width: 80 },
    { prop: 'path', label: '路径' },
    { prop: 'status_code', label: '状态码', width: 80 },
    { prop: 'created_at', label: '时间', width: 180 }
  ]

  const loadData = async () => {
    loading.value = true
    try {
      const res = await request.get<any>({
        url: '/api/auditlog/list',
        params: { page: pagination.value.current, page_size: pagination.value.size }
      })
      tableData.value = res?.records || res || []
      if (res?.total !== undefined) pagination.value.total = res.total
    } finally {
      loading.value = false
    }
  }

  const handlePageChange = (page: number) => {
    pagination.value.current = page
    loadData()
  }

  onMounted(loadData)
</script>
