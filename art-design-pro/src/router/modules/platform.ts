import { AppRouteRecord } from '@/types/router'

export const platformRoutes: AppRouteRecord = {
  path: '/platform',
  name: 'Platform',
  component: '/index/index',
  meta: {
    title: '数据生成平台',
    icon: 'ri:dashboard-line',
    keepAlive: true
  },
  redirect: '/platform/dashboard',
  children: [
    {
      path: 'dashboard',
      name: 'PlatformDashboard',
      component: '/platform/dashboard',
      meta: { title: '仪表盘', keepAlive: false }
    },
    {
      path: 'workbench',
      name: 'PlatformWorkbench',
      component: '/platform/workbench',
      meta: {
        title: '个人工作台',
        keepAlive: true,
        authList: [
          { title: '新建项目', authMark: 'project_add' },
          { title: '数据生成', authMark: 'open_comfy' },
          { title: '数据标注', authMark: 'open_annotation' },
          { title: '编辑项目', authMark: 'project_edit' },
          { title: '删除项目', authMark: 'project_delete' }
        ]
      }
    },
    {
      path: 'prompt',
      name: 'PlatformPrompt',
      component: '/platform/prompt',
      meta: { title: 'Prompt助手', keepAlive: false }
    },
    {
      path: 'stats',
      name: 'PlatformStats',
      component: '/platform/stats',
      meta: { title: '数据统计', keepAlive: true }
    },
    {
      path: 'logs',
      name: 'PlatformLogs',
      component: '/platform/logs',
      meta: { title: '生成日志', keepAlive: true }
    },
    {
      path: 'monitor',
      name: 'PlatformMonitor',
      component: '/platform/monitor',
      meta: { title: '服务器监控', keepAlive: true }
    }
  ]
}
