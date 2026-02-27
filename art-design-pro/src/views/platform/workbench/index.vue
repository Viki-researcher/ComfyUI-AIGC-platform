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
          <ElCard shadow="hover">
            <template #header>
              <div class="flex-cb">
                <div class="truncate font-semibold">{{ p.name }}</div>
                <ElTag size="small" type="info">{{ p.code }}</ElTag>
              </div>
            </template>

            <div class="text-sm text-gray-600 space-y-1">
              <div class="flex-cb">
                <span>创建时间</span>
                <span class="text-gray-800">{{ p.create_time }}</span>
              </div>
              <div class="flex-cb">
                <span>所有者</span>
                <!-- 当 owner_user_name 或 note 为空时，使用 em-dash（—）作为占位符文本，并非 UI 横线元素 -->
                <span class="text-gray-800">{{ p.owner_user_name || '—' }}</span>
              </div>
              <div class="flex-cb">
                <span>生成进度</span>
                <span class="text-gray-800">
                  已生成 {{ p.generated_count }} /
                  {{ p.target_count > 0 ? '目标 ' + p.target_count : '无上限' }}
                </span>
              </div>
              <div class="line-clamp-2 pt-1 text-gray-700">
                <!-- em-dash（—）作为空备注的占位符文本 -->
                {{ p.note || '—' }}
              </div>
            </div>

            <div class="mt-3 flex flex-wrap gap-2">
              <ElTooltip
                :content="isTargetReached(p) ? '已达到目标上限' : ''"
                :disabled="!isTargetReached(p)"
                placement="top"
              >
                <ElButton
                  v-auth="'open_comfy'"
                  type="primary"
                  :disabled="!canOpenComfy(p)"
                  @click="handleOpenComfy(p)"
                  v-ripple
                >
                  数据生成
                </ElButton>
              </ElTooltip>
              <ElButton
                v-auth="'project_edit'"
                :disabled="p.owner_user_id !== userId"
                @click="openEditDialog(p)"
                v-ripple
              >
                编辑
              </ElButton>
              <ElButton
                v-auth="'project_delete'"
                type="danger"
                plain
                :disabled="p.owner_user_id !== userId"
                @click="handleDelete(p)"
                v-ripple
              >
                删除
              </ElButton>
            </div>

            <div v-if="p.owner_user_id !== userId" class="mt-2 text-xs text-gray-500">
              非所有者仅可查看；数据生成由后端 403 校验为准。
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
    fetchUpdateProject
  } from '@/api/projects'
  import { useUserStore } from '@/store/modules/user'
  import { ElMessageBox } from 'element-plus'

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
    target_count: 0
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
      key: 'note',
      label: '备注',
      type: 'input',
      props: { type: 'textarea', rows: 3, placeholder: '可选' }
    },
    {
      key: 'target_count',
      label: '目标生成数量',
      type: 'input',
      props: { type: 'number', placeholder: '0 表示不限制', min: 0 }
    }
  ])

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
    formModel.value = { name: '', code: '', note: '', target_count: 0 }
    dialogVisible.value = true
  }

  const openEditDialog = (p: Api.DataGen.Project) => {
    dialogMode.value = 'edit'
    editingId.value = p.id
    formModel.value = {
      name: p.name,
      code: p.code,
      note: p.note || '',
      target_count: p.target_count || 0
    }
    dialogVisible.value = true
  }

  const handleSave = async () => {
    if (!formModel.value.name || !formModel.value.code) return
    saving.value = true
    try {
      const targetCount = Number(formModel.value.target_count) || 0
      if (dialogMode.value === 'create') {
        await fetchCreateProject({
          name: formModel.value.name,
          code: formModel.value.code,
          note: formModel.value.note,
          target_count: targetCount
        })
      } else if (editingId.value) {
        await fetchUpdateProject(editingId.value, {
          name: formModel.value.name,
          note: formModel.value.note,
          target_count: targetCount
        })
      }
      dialogVisible.value = false
      await loadProjects()
    } finally {
      saving.value = false
    }
  }

  const isTargetReached = (p: Api.DataGen.Project) => {
    return p.target_count > 0 && p.generated_count >= p.target_count
  }

  const canOpenComfy = (p: Api.DataGen.Project) => {
    return p.owner_user_id === userId.value && !isTargetReached(p)
  }

  const handleOpenComfy = async (p: Api.DataGen.Project) => {
    const { comfy_url } = await fetchOpenComfy(p.id)
    window.open(comfy_url, '_blank')
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
  }
</style>
