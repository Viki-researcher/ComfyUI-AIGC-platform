<template>
  <div class="p-4">
    <ElCard shadow="never">
      <div class="text-lg font-semibold mb-2">API 管理</div>
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

  defineOptions({ name: 'SystemApi' })

  const loading = ref(false)
  const tableData = ref<any[]>([])
  const pagination = ref({ current: 1, size: 20, total: 0 })

  const columns = [
    { prop: 'id', label: 'ID', width: 80 },
    { prop: 'method', label: '请求方法', width: 100 },
    { prop: 'path', label: '路径' },
    { prop: 'summary', label: '描述' },
    { prop: 'tags', label: '标签', width: 140 }
  ]

  const loadData = async () => {
    loading.value = true
    try {
      const res = await request.get<any>({
        url: '/api/api/list',
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
