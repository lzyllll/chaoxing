<script setup lang="ts">
import { computed, h } from 'vue'
import {
  NAvatar,
  NBreadcrumb,
  NBreadcrumbItem,
  NButton,
  NIcon,
  NLayout,
  NLayoutContent,
  NLayoutHeader,
  NLayoutSider,
  NMenu,
  NSpace,
} from 'naive-ui'
import {
  CheckmarkCircleOutline,
  DocumentTextOutline,
  HelpCircleOutline,
  HomeOutline,
  ListOutline,
  PersonCircleOutline,
} from '@vicons/ionicons5'
import type { MenuOption } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

function renderIcon(icon: typeof HomeOutline) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = computed<MenuOption[]>(() => [
  {
    label: '总览',
    key: 'dashboard',
    icon: renderIcon(HomeOutline),
  },
  {
    label: '账号管理',
    key: 'accounts',
    icon: renderIcon(PersonCircleOutline),
  },
  {
    label: '创建任务',
    key: 'task-create',
    icon: renderIcon(CheckmarkCircleOutline),
  },
  {
    label: '任务监控',
    key: 'tasks',
    icon: renderIcon(ListOutline),
  },
  {
    label: '人工确认',
    key: 'decisions',
    icon: renderIcon(DocumentTextOutline),
  },
])

const activeKey = computed(() => {
  const name = route.name
  if (name === 'account-detail') {
    return 'accounts'
  }
  if (name === 'task-detail') {
    return 'tasks'
  }
  return typeof name === 'string' ? name : 'dashboard'
})

const breadcrumbItems = computed(() => {
  const matched = route.matched.filter((item) => item.meta?.title)
  return matched.map((item) => ({
    label: String(item.meta.title),
    key: item.path,
  }))
})

function handleMenuSelect(key: string): void {
  const pathMap: Record<string, string> = {
    dashboard: '/',
    accounts: '/accounts',
    'task-create': '/tasks/create',
    tasks: '/tasks',
    decisions: '/decisions',
  }

  void router.push(pathMap[key] ?? '/')
}
</script>

<template>
  <n-layout has-sider position="absolute" class="app-shell">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="80"
      :width="240"
      :collapsed="appStore.collapsed"
      show-trigger
      class="app-shell__sider"
      @update:collapsed="appStore.collapsed = $event"
    >
      <div class="app-shell__brand">
        <div class="app-shell__brand-mark">CX</div>
        <div v-if="!appStore.collapsed" class="app-shell__brand-text">
          <strong>Chaoxing 控制台</strong>
          <span>多账号任务编排</span>
        </div>
      </div>
      <n-menu :value="activeKey" :options="menuOptions" @update:value="handleMenuSelect" />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered class="app-shell__header">
        <div>
          <n-breadcrumb>
            <n-breadcrumb-item v-for="item in breadcrumbItems" :key="item.key">
              {{ item.label }}
            </n-breadcrumb-item>
          </n-breadcrumb>
          <h1 class="app-shell__title">{{ route.meta.title ?? 'Chaoxing 控制台' }}</h1>
        </div>

        <n-space align="center">
          <n-button quaternary circle @click="appStore.toggleTheme">
            <template #icon>
              <n-icon>
                <component :is="appStore.isDark ? HelpCircleOutline : HomeOutline" />
              </n-icon>
            </template>
          </n-button>
          <n-avatar round size="small">管</n-avatar>
        </n-space>
      </n-layout-header>

      <n-layout-content content-style="padding: 20px;">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-shell__sider {
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.04);
}

.app-shell__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px 16px;
}

.app-shell__brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  font-weight: 700;
}

.app-shell__brand-text {
  display: flex;
  flex-direction: column;
}

.app-shell__brand-text span {
  color: var(--muted-text);
  font-size: 12px;
}

.app-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
}

.app-shell__title {
  margin: 8px 0 0;
  font-size: 24px;
  line-height: 1.2;
}
</style>
