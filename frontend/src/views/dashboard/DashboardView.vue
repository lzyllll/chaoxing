<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getDashboardSummary, getHealth, getTasks } from '@/api/client'
import type { HealthResponse, TaskSummary } from '@/types'
import { formatPercent } from '@/utils/format'

const loading = ref(true)
const health = ref<HealthResponse | null>(null)
const summary = ref({
  accountCount: 0,
  activeTaskCount: 0,
  pendingDecisionCount: 0,
  successRate: 0,
})
const recentTasks = ref<TaskSummary[]>([])

onMounted(async () => {
  const [healthData, summaryData, tasks] = await Promise.all([
    getHealth(),
    getDashboardSummary(),
    getTasks(),
  ])

  health.value = healthData
  summary.value = summaryData
  recentTasks.value = tasks.slice(0, 3)
  loading.value = false
})
</script>

<template>
  <n-space vertical size="large">
    <n-grid x-gap="16" y-gap="16" cols="1 s:2 l:4" responsive="screen">
      <n-grid-item>
        <n-card :bordered="false" class="metric-card">
          <n-statistic label="账号数量" :value="summary.accountCount" />
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card :bordered="false" class="metric-card">
          <n-statistic label="运行中任务" :value="summary.activeTaskCount" />
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card :bordered="false" class="metric-card">
          <n-statistic label="待人工确认" :value="summary.pendingDecisionCount" />
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card :bordered="false" class="metric-card">
          <n-statistic label="成功率" :value="summary.successRate" suffix="%" />
        </n-card>
      </n-grid-item>
    </n-grid>

    <n-grid x-gap="16" y-gap="16" cols="1 l:3" responsive="screen">
      <n-grid-item span="2">
        <n-card title="最近任务" :bordered="false">
          <n-data-table
            :loading="loading"
            :columns="[
              { title: '任务 ID', key: 'id' },
              { title: '账号', key: 'accountName' },
              { title: '状态', key: 'status' },
              { title: '进度', key: 'progressPct', render: (row: TaskSummary) => formatPercent(row.progressPct) },
            ]"
            :data="recentTasks"
            :pagination="false"
          />
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card title="后端状态" :bordered="false">
          <n-descriptions label-placement="top" :column="1" bordered>
            <n-descriptions-item label="API 状态">
              {{ health?.status ?? '--' }}
            </n-descriptions-item>
            <n-descriptions-item label="版本">
              {{ health?.version ?? '--' }}
            </n-descriptions-item>
            <n-descriptions-item label="默认地址">
              http://127.0.0.1:8000
            </n-descriptions-item>
          </n-descriptions>
        </n-card>
      </n-grid-item>
    </n-grid>
  </n-space>
</template>

<style scoped>
.metric-card {
  border-radius: 16px;
}
</style>
