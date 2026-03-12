<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { createTaskWebSocket, getTaskDetail } from '@/api/client'
import type { AnswerRecordItem, TaskEventItem, TaskLogItem, TaskSummary } from '@/types'
import { formatConfidence, formatDateTime, formatPercent } from '@/utils/format'

const route = useRoute()
const loading = ref(true)
const task = ref<TaskSummary | null>(null)
const events = ref<TaskEventItem[]>([])
const logs = ref<TaskLogItem[]>([])
const answers = ref<AnswerRecordItem[]>([])
const wsStatus = ref<'connecting' | 'connected' | 'disconnected'>('connecting')
let taskSocket: WebSocket | null = null

const taskId = computed(() => Number(route.params.id))

onMounted(async () => {
  const detail = await getTaskDetail(taskId.value)
  task.value = detail.task
  events.value = detail.events
  logs.value = detail.logs
  answers.value = detail.answers
  loading.value = false
  connectTaskSocket()
})

onBeforeUnmount(() => {
  taskSocket?.close()
})

function connectTaskSocket(): void {
  taskSocket = createTaskWebSocket(taskId.value)
  wsStatus.value = 'connecting'

  taskSocket.onopen = () => {
    wsStatus.value = 'connected'
  }

  taskSocket.onclose = () => {
    wsStatus.value = 'disconnected'
  }

  taskSocket.onmessage = (event) => {
    const payload = JSON.parse(event.data) as {
      type: string
      message?: string
      task?: TaskSummary
      events?: TaskEventItem[]
      logs?: TaskLogItem[]
      answers?: AnswerRecordItem[]
    }

    if (payload.type === 'snapshot') {
      task.value = payload.task ?? task.value
      events.value = payload.events ?? events.value
      logs.value = payload.logs ?? logs.value
      answers.value = payload.answers ?? answers.value
      return
    }

    if (payload.type === 'error') {
      wsStatus.value = 'disconnected'
    }
  }
}
</script>

<template>
  <n-space vertical size="large">
    <n-card title="任务概览" :bordered="false" :loading="loading">
      <n-space vertical size="medium">
        <n-alert :show-icon="false" type="info">
          WebSocket 状态：{{ wsStatus }}
        </n-alert>
        <n-descriptions v-if="task" bordered label-placement="top" :column="4">
          <n-descriptions-item label="任务 ID">{{ task.id }}</n-descriptions-item>
          <n-descriptions-item label="状态">{{ task.status }}</n-descriptions-item>
          <n-descriptions-item label="进度">{{ formatPercent(task.progressPct) }}</n-descriptions-item>
          <n-descriptions-item label="账号">{{ task.accountName }}</n-descriptions-item>
          <n-descriptions-item label="当前课程">{{ task.currentCourse || '--' }}</n-descriptions-item>
          <n-descriptions-item label="当前章节">{{ task.currentChapter || '--' }}</n-descriptions-item>
          <n-descriptions-item label="当前任务点">{{ task.currentJob || '--' }}</n-descriptions-item>
          <n-descriptions-item label="创建时间">{{ formatDateTime(task.createdAt) }}</n-descriptions-item>
        </n-descriptions>
      </n-space>
    </n-card>

    <n-grid x-gap="16" y-gap="16" cols="1 l:2" responsive="screen">
      <n-grid-item>
        <n-card title="事件流" :bordered="false">
          <n-timeline>
            <n-timeline-item v-for="event in events" :key="event.id" :title="event.eventType" :content="JSON.stringify(event.payload)" :time="formatDateTime(event.createdAt)" />
          </n-timeline>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card title="运行日志" :bordered="false">
          <n-list bordered>
            <n-list-item v-for="log in logs" :key="log.id">
              <n-space vertical size="small">
                <n-space justify="space-between">
                  <n-tag size="small">{{ log.level }}</n-tag>
                  <n-text depth="3">{{ formatDateTime(log.createdAt) }}</n-text>
                </n-space>
                <n-text>{{ log.message }}</n-text>
              </n-space>
            </n-list-item>
          </n-list>
        </n-card>
      </n-grid-item>
    </n-grid>

    <n-card title="答题记录" :bordered="false">
      <n-data-table
        :columns="[
          { title: '题目 ID', key: 'questionId' },
          { title: '题型', key: 'questionType' },
          { title: '题目', key: 'questionTitle' },
          { title: '答案', key: 'finalAnswer' },
          { title: '来源', key: 'answerSource' },
          { title: '置信度', key: 'confidence', render: (row: AnswerRecordItem) => formatConfidence(row.confidence) },
          { title: '决策', key: 'decision' },
          { title: '提交结果', key: 'submitResult' },
        ]"
        :data="answers"
        :pagination="false"
      />
    </n-card>
  </n-space>
</template>
