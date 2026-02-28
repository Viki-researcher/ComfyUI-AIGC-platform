<template>
  <div class="platform-workbench art-full-height">
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">个人工作台</div>
          <div class="text-sm text-gray-500">项目卡片、ComfyUI 状态与入口</div>
        </div>
        <div class="flex gap-2">
          <ElButton v-auth="'project_add'" type="primary" @click="openCreateDialog" v-ripple>
            新建项目
          </ElButton>
          <ElButton @click="loadProjects" :loading="loading" v-ripple>刷新</ElButton>
        </div>
      </div>
    </ElCard>

    <ElCard class="art-table-card" shadow="never">
      <ElRow :gutter="12">
        <ElCol v-for="p in projects" :key="p.id" :xs="24" :sm="12" :md="8" :lg="6" class="mb-3">
          <ElCard shadow="hover" class="project-card">
            <template #header>
              <div class="flex-cb">
                <div class="truncate font-semibold">{{ p.name }}</div>
                <ElTag size="small" type="info">{{ p.code }}</ElTag>
              </div>
            </template>

            <!-- 进度指示器 -->
            <div class="flex items-center gap-3 mb-3">
              <ElProgress
                type="circle"
                :percentage="progressPercent(p)"
                :width="56"
                :stroke-width="5"
                :color="progressColor(p)"
              >
                <template #default>
                  <span class="text-xs font-semibold">{{ progressPercent(p) }}%</span>
                </template>
              </ElProgress>
              <div class="flex-1 text-sm">
                <div class="text-gray-800 font-medium">
                  {{ p.generated_count }} / {{ p.target_count }} 张
                </div>
                <div class="text-gray-500 text-xs mt-1">
                  {{ p.owner_user_name || '—' }} · {{ p.create_time?.slice(0, 10) }}
                </div>
              </div>
            </div>

            <!-- 服务状态灯 -->
            <div class="flex gap-3 mb-3 text-xs">
              <div class="flex items-center gap-1">
                <span class="status-dot" :class="statusClass(p.comfy_status)"></span>
                <span class="text-gray-600">ComfyUI</span>
              </div>
              <div class="flex items-center gap-1">
                <span class="status-dot" :class="statusClass(p.annotation_status)"></span>
                <span class="text-gray-600">标注</span>
              </div>
            </div>

            <div v-if="p.note" class="line-clamp-1 text-xs text-gray-500 mb-2">{{ p.note }}</div>

            <div v-if="isTargetReached(p)" class="text-xs text-green-600 mb-2 flex items-center gap-1">
              <span>✓</span> 已达目标数量，编辑项目可调整上限
            </div>

            <div class="flex flex-wrap gap-2">
              <ElButton
                v-auth="'open_comfy'"
                type="primary"
                size="small"
                :disabled="!canOpenComfy(p)"
                :loading="comfyLoading === p.id"
                @click="handleOpenComfy(p)"
                v-ripple
              >
                数据生成
              </ElButton>
              <ElButton
                v-auth="'open_annotation'"
                type="success"
                size="small"
                :disabled="p.owner_user_id !== userId"
                :loading="annotationLoading === p.id"
                @click="handleOpenAnnotation(p)"
                v-ripple
              >
                数据标注
              </ElButton>
              <ElButton
                v-auth="'project_edit'"
                size="small"
                :disabled="p.owner_user_id !== userId"
                @click="openEditDialog(p)"
                v-ripple
              >
                编辑
              </ElButton>
              <ElButton
                v-auth="'project_delete'"
                type="danger"
                size="small"
                plain
                :disabled="p.owner_user_id !== userId"
                @click="handleDelete(p)"
                v-ripple
              >
                删除
              </ElButton>
            </div>
          </ElCard>
        </ElCol>
      </ElRow>

      <ElEmpty v-if="!loading && projects.length === 0" description="暂无项目" />
    </ElCard>

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="560px" append-to-body>
      <ArtForm
        ref="formRef"
        v-model="formModel"
        :items="formItems"
        label-position="top"
        :showReset="false"
        :showSubmit="false"
      />
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="dialogVisible = false" v-ripple>取消</ElButton>
          <ElButton type="primary" :loading="saving" @click="handleSave" v-ripple>保存</ElButton>
        </div>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
  import {
    fetchCreateProject,
    fetchDeleteProject,
    fetchGetProjects,
    fetchOpenComfy,
    fetchOpenAnnotation,
    fetchUpdateProject
  } from '@/api/projects'
  import { useUserStore } from '@/store/modules/user'
  import { ElMessage, ElMessageBox } from 'element-plus'

  defineOptions({ name: 'PlatformWorkbench' })

  const userStore = useUserStore()
  const userId = computed(() => userStore.getUserInfo.userId)

  const loading = ref(false)
  const saving = ref(false)
  const projects = ref<Api.DataGen.Project[]>([])

  const dialogVisible = ref(false)
  const dialogMode = ref<'create' | 'edit'>('create')
  const editingId = ref<number | null>(null)
  const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新建项目' : '编辑项目'))

  const formModel = ref<Record<string, any>>({
    name: '',
    code: '',
    note: '',
    target_count: 1000
  })

  const formItems = computed(() => [
    {
      key: 'name',
      label: '项目名称',
      type: 'input',
      props: { placeholder: '请输入项目名称', clearable: true }
    },
    {
      key: 'code',
      label: '项目号',
      type: 'input',
      props: { placeholder: '例如 PRJ-001', clearable: true, disabled: dialogMode.value === 'edit' }
    },
    {
      key: 'target_count',
      label: '目标生成数量',
      type: 'number',
      props: { min: 1, max: 100000, placeholder: '1000' }
    },
    {
      key: 'note',
      label: '备注',
      type: 'input',
      props: { type: 'textarea', rows: 2, placeholder: '可选' }
    }
  ])

  const progressPercent = (p: Api.DataGen.Project) => {
    if (!p.target_count || p.target_count <= 0) return 0
    return Math.min(100, Math.round((p.generated_count / p.target_count) * 100))
  }

  const progressColor = (p: Api.DataGen.Project) => {
    const pct = progressPercent(p)
    if (pct >= 100) return '#67c23a'
    if (pct >= 60) return '#409eff'
    return '#e6a23c'
  }

  const statusClass = (status: string) => {
    if (status === 'online') return 'status-online'
    if (status === 'offline') return 'status-offline'
    return 'status-stopped'
  }

  const loadProjects = async () => {
    loading.value = true
    try {
      projects.value = await fetchGetProjects()
    } finally {
      loading.value = false
    }
  }

  onMounted(loadProjects)

  const openCreateDialog = () => {
    dialogMode.value = 'create'
    editingId.value = null
    formModel.value = { name: '', code: '', note: '', target_count: 1000 }
    dialogVisible.value = true
  }

  const openEditDialog = (p: Api.DataGen.Project) => {
    dialogMode.value = 'edit'
    editingId.value = p.id
    formModel.value = { name: p.name, code: p.code, note: p.note || '', target_count: p.target_count }
    dialogVisible.value = true
  }

  const handleSave = async () => {
    if (!formModel.value.name || !formModel.value.code) return
    saving.value = true
    try {
      if (dialogMode.value === 'create') {
        await fetchCreateProject({
          name: formModel.value.name,
          code: formModel.value.code,
          note: formModel.value.note,
          target_count: formModel.value.target_count
        })
      } else if (editingId.value) {
        await fetchUpdateProject(editingId.value, {
          name: formModel.value.name,
          note: formModel.value.note,
          target_count: formModel.value.target_count
        })
      }
      dialogVisible.value = false
      await loadProjects()
    } finally {
      saving.value = false
    }
  }

  const isTargetReached = (p: Api.DataGen.Project) =>
    p.target_count > 0 && p.generated_count >= p.target_count

  const canOpenComfy = (p: Api.DataGen.Project) =>
    p.owner_user_id === userId.value && !isTargetReached(p)

  const comfyLoading = ref<number | null>(null)
  const annotationLoading = ref<number | null>(null)

  const handleOpenComfy = async (p: Api.DataGen.Project) => {
    comfyLoading.value = p.id
    try {
      const { comfy_url } = await fetchOpenComfy(p.id)
      window.open(comfy_url, '_blank')
    } catch (e: any) {
      ElMessage.error(e?.message || '启动 ComfyUI 服务失败')
    } finally {
      comfyLoading.value = null
    }
  }

  const handleOpenAnnotation = async (p: Api.DataGen.Project) => {
    annotationLoading.value = p.id
    try {
      const { annotation_url } = await fetchOpenAnnotation(p.id)
      window.open(annotation_url, '_blank')
    } catch (e: any) {
      ElMessage.error(e?.message || '启动标注服务失败')
    } finally {
      annotationLoading.value = null
    }
  }

  const handleDelete = async (p: Api.DataGen.Project) => {
    await ElMessageBox.confirm(`确认删除项目「${p.name}」吗？`, '提示', { type: 'warning' })
    await fetchDeleteProject(p.id)
    await loadProjects()
  }
</script>

<style scoped>
  .platform-workbench {
    padding: 12px;
    overflow-y: auto;
  }

  .platform-workbench > :deep(.el-card) {
    flex-shrink: 0;
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

  .status-offline {
    background-color: #f56c6c;
    box-shadow: 0 0 4px #f56c6c;
  }

  .status-stopped {
    background-color: #c0c4cc;
  }
</style>
