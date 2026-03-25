<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NPopconfirm, NSpace, useMessage } from 'naive-ui'

import { deleteTask, getTasks } from '@/api/client'
import type { TaskSummary } from '@/types'
import { formatDateTime, formatPercent } from '@/utils/format'

const router = useRouter()
const message = useMessage()
const loading = ref(true)
const tasks = ref<TaskSummary[]>([])
const deletingTaskId = ref<number | null>(null)
let timer: number | null = null

const columns = computed(() => [
  { title: '任务 ID', key: 'id' },
  { title: '账号', key: 'accountName' },
  { title: '状态', key: 'status' },
  {
    title: '课程',
    key: 'selectedCourses',
    render: (row: TaskSummary) => row.selectedCourses.join('、'),
  },
  {
    title: '进度',
    key: 'progressPct',
    render: (row: TaskSummary) => formatPercent(row.progressPct),
  },
  {
    title: '创建时间',
    key: 'createdAt',
    render: (row: TaskSummary) => formatDateTime(row.createdAt),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: TaskSummary) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              secondary: true,
              onClick: () => openTask(row.id),
            },
            { default: () => '查看' },
          ),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDeleteTask(row),
            },
            {
              trigger: () =>
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error',
                    ghost: true,
                    loading: deletingTaskId.value === row.id,
                  },
                  { default: () => '删除' },
                ),
              default: () => `删除任务 #${row.id} 及其运行记录？`,
            },
          ),
        ],
      }),
  },
])

async function loadTasks(): Promise<void> {
  tasks.value = await getTasks()
  loading.value = false
}

onMounted(async () => {
  await loadTasks()
  timer = window.setInterval(() => {
    void loadTasks()
  }, 5000)
})

onBeforeUnmount(() => {
  if (timer !== null) {
    window.clearInterval(timer)
  }
})

function openTask(taskId: number): void {
  void router.push(`/tasks/${taskId}`)
}

async function handleDeleteTask(task: TaskSummary): Promise<void> {
  deletingTaskId.value = task.id
  try {
    await deleteTask(task.id)
    message.success('任务已删除')
    await loadTasks()
  } catch (error: unknown) {
    const maybeAxiosError = error as { response?: { status?: number; data?: { detail?: string } } }
    if (maybeAxiosError?.response?.status === 409) {
      message.error(maybeAxiosError.response.data?.detail ?? '运行中的任务不能删除')
    } else {
      message.error('删除任务失败')
    }
  } finally {
    deletingTaskId.value = null
  }
}
</script>

<template>
  <n-space vertical size="large">
    <n-card title="任务监控" :bordered="false">
      <n-data-table :loading="loading" :columns="columns" :data="tasks" :pagination="false" />
    </n-card>

    <n-grid x-gap="16" y-gap="16" cols="1 l:2" responsive="screen">
      <n-grid-item v-for="task in tasks" :key="task.id">
        <n-card hoverable :bordered="false" @click="openTask(task.id)">
          <n-space vertical size="small">
            <n-space justify="space-between">
              <n-text strong>任务 #{{ task.id }}</n-text>
              <n-tag>{{ task.status }}</n-tag>
            </n-space>
            <n-text depth="3">账号：{{ task.accountName }}</n-text>
            <n-progress type="line" :percentage="Math.round(task.progressPct)" />
            <n-text depth="3">当前课程：{{ task.currentCourse || '--' }}</n-text>
            <n-text depth="3">当前章节：{{ task.currentChapter || '--' }}</n-text>
            <n-space justify="end">
              <n-popconfirm @positive-click="handleDeleteTask(task)">
                <template #trigger>
                  <n-button
                    size="small"
                    type="error"
                    ghost
                    :loading="deletingTaskId === task.id"
                    @click.stop
                  >
                    删除
                  </n-button>
                </template>
                删除任务 #{{ task.id }} 及其运行记录？
              </n-popconfirm>
            </n-space>
          </n-space>
        </n-card>
      </n-grid-item>
    </n-grid>
  </n-space>
</template>
