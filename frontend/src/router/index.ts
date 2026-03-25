import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import { pinia } from '@/stores/pinia'
import { useAdminAuthStore } from '@/stores/adminAuth'
import AccountDetailView from '@/views/accounts/AccountDetailView.vue'
import AccountsView from '@/views/accounts/AccountsView.vue'
import AdminLoginView from '@/views/admin/AdminLoginView.vue'
import DashboardView from '@/views/dashboard/DashboardView.vue'
import DecisionsView from '@/views/decisions/DecisionsView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import TaskCreateView from '@/views/tasks/TaskCreateView.vue'
import TaskDetailView from '@/views/tasks/TaskDetailView.vue'
import TasksView from '@/views/tasks/TasksView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/admin/login',
    name: 'admin-login',
    component: AdminLoginView,
    meta: { title: '管理员登录', public: true },
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: DashboardView,
        meta: { title: '总览' },
      },
      {
        path: 'accounts',
        name: 'accounts',
        component: AccountsView,
        meta: { title: '账号管理' },
      },
      {
        path: 'accounts/:id',
        name: 'account-detail',
        component: AccountDetailView,
        meta: { title: '账号详情' },
      },
      {
        path: 'tasks/create',
        name: 'task-create',
        component: TaskCreateView,
        meta: { title: '创建任务' },
      },
      {
        path: 'tasks',
        name: 'tasks',
        component: TasksView,
        meta: { title: '任务监控' },
      },
      {
        path: 'tasks/:id',
        name: 'task-detail',
        component: TaskDetailView,
        meta: { title: '任务详情' },
      },
      {
        path: 'decisions',
        name: 'decisions',
        component: DecisionsView,
        meta: { title: '人工确认' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: NotFoundView,
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const authStore = useAdminAuthStore(pinia)
  await authStore.ensureSession()

  if (to.name === 'admin-login') {
    if (authStore.authenticated) {
      const redirect = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/')
        ? to.query.redirect
        : '/'
      return redirect === to.fullPath ? '/' : redirect
    }
    return true
  }

  if (authStore.requiresLogin) {
    return {
      name: 'admin-login',
      query: { redirect: to.fullPath },
    }
  }

  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'Chaoxing 控制台'
  document.title = `${title} · Chaoxing 控制台`
})

export default router
