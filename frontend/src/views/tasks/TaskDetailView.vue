<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'

import { createTaskWebSocket, getTaskDetail } from '@/api/client'
import type { AnswerRecordItem, TaskEventItem, TaskLogItem, TaskSummary } from '@/types'
import { formatConfidence, formatDateTime, formatPercent } from '@/utils/format'

const route = useRoute()
const message = useMessage()
const loading = ref(true)
const task = ref<TaskSummary | null>(null)
const events = ref<TaskEventItem[]>([])
const logs = ref<TaskLogItem[]>([])
const answers = ref<AnswerRecordItem[]>([])
const wsStatus = ref<'connecting' | 'connected' | 'disconnected'>('connecting')
const eventVisibleCount = ref(8)
const logVisibleCount = ref(8)
const showEvents = ref(false)
const showLogs = ref(false)
let taskSocket: WebSocket | null = null

const taskId = computed(() => Number(route.params.id))
const latestVideoEvent = computed(() =>
  [...events.value]
    .reverse()
    .find((event) => event.eventType === 'video_progress' || event.eventType === 'video_completed'),
)
const answerGroups = computed(() => {
  const groups = new Map<string, { key: string; courseTitle: string; chapterTitle: string; items: AnswerRecordItem[] }>()

  for (const item of answers.value) {
    const courseTitle = item.courseTitle || '未命名课程'
    const chapterTitle = item.chapterTitle || '未识别章节'
    const key = `${courseTitle}__${chapterTitle}`

    if (!groups.has(key)) {
      groups.set(key, {
        key,
        courseTitle,
        chapterTitle,
        items: [],
      })
    }

    groups.get(key)?.items.push(item)
  }

  return [...groups.values()]
})
const visibleEvents = computed(() =>
  [...events.value]
    .sort((left, right) => right.seq - left.seq || right.id - left.id)
    .slice(0, eventVisibleCount.value),
)
const visibleLogs = computed(() =>
  [...logs.value]
    .sort((left, right) => {
      const leftTime = new Date(left.createdAt).getTime()
      const rightTime = new Date(right.createdAt).getTime()
      return rightTime - leftTime || right.id - left.id
    })
    .slice(0, logVisibleCount.value),
)
const canLoadMoreEvents = computed(() => eventVisibleCount.value < events.value.length)
const canLoadMoreLogs = computed(() => logVisibleCount.value < logs.value.length)
const chapterOverview = computed(() => {
  type ChapterRow = {
    key: string
    chapterId: string
    chapterTitle: string
    courseTitle: string
    status: 'pending' | 'running' | 'completed' | 'failed' | 'not_open'
    progressPct: number
    answerCount: number
    answerSummary: string
  }

  const courseMap = new Map<string, { key: string; courseTitle: string; chapters: ChapterRow[] }>()
  const chapterMap = new Map<string, ChapterRow>()
  const answerCountMap = new Map<string, number>()

  for (const answer of answers.value) {
    const key = `${answer.courseTitle || '未命名课程'}__${answer.chapterTitle || '未识别章节'}`
    answerCountMap.set(key, (answerCountMap.get(key) ?? 0) + 1)
  }

  function ensureCourse(courseTitle: string, courseId?: string): { key: string; courseTitle: string; chapters: ChapterRow[] } {
    const key = `${courseId || courseTitle}`
    if (!courseMap.has(key)) {
      courseMap.set(key, { key, courseTitle, chapters: [] })
    }
    return courseMap.get(key)!
  }

  function ensureChapter(
    courseTitle: string,
    chapterTitle: string,
    chapterId?: string,
    courseId?: string,
  ): ChapterRow {
    const rowKey = `${courseId || courseTitle}__${chapterId || chapterTitle}`
    if (!chapterMap.has(rowKey)) {
      const row: ChapterRow = {
        key: rowKey,
        chapterId: String(chapterId || ''),
        chapterTitle,
        courseTitle,
        status: 'pending',
        progressPct: 0,
        answerCount: answerCountMap.get(`${courseTitle}__${chapterTitle}`) ?? 0,
        answerSummary: '',
      }
      chapterMap.set(rowKey, row)
      ensureCourse(courseTitle, courseId).chapters.push(row)
    }
    return chapterMap.get(rowKey)!
  }

  for (const event of [...events.value].sort((left, right) => left.seq - right.seq || left.id - right.id)) {
    const payload = event.payload
    const courseTitle = String(payload.courseTitle ?? '未命名课程')
    const courseId = String(payload.courseId ?? '')

    if (event.eventType === 'course_chapters_loaded') {
      ensureCourse(courseTitle, courseId)
      const chapters = Array.isArray(payload.chapters) ? payload.chapters : []
      for (const chapter of chapters) {
        const row = ensureChapter(
          courseTitle,
          String((chapter as Record<string, unknown>).chapterTitle ?? '未识别章节'),
          String((chapter as Record<string, unknown>).chapterId ?? ''),
          courseId,
        )
        if ((chapter as Record<string, unknown>).hasFinished) {
          row.status = 'completed'
          row.progressPct = 100
        }
      }
      continue
    }

    const chapterTitle = String(payload.chapterTitle ?? '')
    const chapterId = String(payload.chapterId ?? '')
    if (!chapterTitle) {
      continue
    }

    const row = ensureChapter(courseTitle, chapterTitle, chapterId, courseId)

    if (event.eventType === 'chapter_started') {
      row.status = row.status === 'completed' ? 'completed' : 'running'
      row.progressPct = Math.max(row.progressPct, 1)
    }
    if (event.eventType === 'video_progress') {
      row.status = row.status === 'completed' ? 'completed' : 'running'
      row.progressPct = Math.max(row.progressPct, Number(payload.progressPct ?? 0))
    }
    if (event.eventType === 'video_completed') {
      row.status = row.status === 'completed' ? 'completed' : 'running'
      row.progressPct = Math.max(row.progressPct, 100)
    }
    if (event.eventType === 'chapter_completed') {
      row.status = 'completed'
      row.progressPct = 100
    }
    if (event.eventType === 'chapter_failed') {
      row.status = 'failed'
    }
    if (event.eventType === 'chapter_not_open') {
      row.status = 'not_open'
    }
  }

  for (const course of courseMap.values()) {
    for (const chapter of course.chapters) {
      chapter.answerCount = answerCountMap.get(`${chapter.courseTitle}__${chapter.chapterTitle}`) ?? 0
      chapter.answerSummary = chapter.answerCount > 0 ? `已记录 ${chapter.answerCount} 题` : '暂无答题记录'
    }
  }

  return [...courseMap.values()]
})

function loadMoreEvents(): void {
  eventVisibleCount.value += 8
}

function loadMoreLogs(): void {
  logVisibleCount.value += 8
}

function chapterStatusLabel(status: string): string {
  if (status === 'completed') return '已完成'
  if (status === 'running') return '进行中'
  if (status === 'failed') return '失败'
  if (status === 'not_open') return '未开放'
  return '未开始'
}

function chapterStatusType(status: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'info'
  if (status === 'failed') return 'error'
  if (status === 'not_open') return 'warning'
  return 'default'
}

onMounted(async () => {
  try {
    const detail = await getTaskDetail(taskId.value)
    task.value = detail.task
    events.value = detail.events
    logs.value = detail.logs
    answers.value = detail.answers
    connectTaskSocket()
  } catch (error) {
    message.error('任务详情加载失败')
  } finally {
    loading.value = false
  }
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
      message.error(payload.message ?? '任务连接已断开')
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
        <n-card v-if="latestVideoEvent" size="small" embedded>
          <n-space justify="space-between" align="center">
            <div>
              <n-text strong>{{ String(latestVideoEvent.payload.jobName ?? '视频任务') }}</n-text>
              <n-text depth="3" style="display: block">
                {{ String(latestVideoEvent.payload.chapterTitle ?? '--') }}
              </n-text>
            </div>
            <n-progress
              type="circle"
              :percentage="Math.round(Number(latestVideoEvent.payload.progressPct ?? 0))"
              :show-indicator="true"
              :width="74"
            />
          </n-space>
        </n-card>
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
        <n-card title="章节总览" :bordered="false">
          <n-empty v-if="chapterOverview.length === 0" description="课程章节尚未加载，任务开始后会在这里展示" />
          <n-collapse v-else>
            <n-collapse-item
              v-for="course in chapterOverview"
              :key="course.key"
              :title="course.courseTitle"
              :name="course.key"
            >
              <n-list bordered>
                <n-list-item v-for="chapter in course.chapters" :key="chapter.key">
                  <n-space vertical size="small" style="width: 100%">
                    <n-space justify="space-between" align="center">
                      <n-text strong>{{ chapter.chapterTitle }}</n-text>
                      <n-tag :type="chapterStatusType(chapter.status)">
                        {{ chapterStatusLabel(chapter.status) }}
                      </n-tag>
                    </n-space>
                    <n-progress type="line" :percentage="Math.round(chapter.progressPct)" :show-indicator="true" />
                    <n-space justify="space-between">
                      <n-text depth="3">{{ chapter.answerSummary }}</n-text>
                      <n-text depth="3">{{ formatPercent(chapter.progressPct) }}</n-text>
                    </n-space>
                  </n-space>
                </n-list-item>
              </n-list>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card title="事件流" :bordered="false">
          <template #header-extra>
            <n-button quaternary size="small" @click="showEvents = !showEvents">
              {{ showEvents ? '收起' : '展开' }}
            </n-button>
          </template>
          <n-empty v-if="events.length === 0" description="暂无事件" />
          <n-space v-else-if="!showEvents" justify="center">
            <n-text depth="3">默认收起，点击展开查看最新 8 条事件</n-text>
          </n-space>
          <template v-else>
            <div class="scroll-panel">
              <n-list bordered>
                <n-list-item v-for="event in visibleEvents" :key="event.id">
                  <n-space vertical size="small" style="width: 100%">
                    <n-space justify="space-between">
                      <n-tag size="small" type="info">{{ event.eventType }}</n-tag>
                      <n-text depth="3">{{ formatDateTime(event.createdAt) }}</n-text>
                    </n-space>
                    <n-text>{{ JSON.stringify(event.payload) }}</n-text>
                  </n-space>
                </n-list-item>
              </n-list>
            </div>
            <n-space v-if="canLoadMoreEvents" justify="center" style="margin-top: 12px">
              <n-button quaternary @click="loadMoreEvents">查看更早的事件</n-button>
            </n-space>
          </template>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card title="运行日志" :bordered="false">
          <template #header-extra>
            <n-button quaternary size="small" @click="showLogs = !showLogs">
              {{ showLogs ? '收起' : '展开' }}
            </n-button>
          </template>
          <n-empty v-if="logs.length === 0" description="暂无日志" />
          <n-space v-else-if="!showLogs" justify="center">
            <n-text depth="3">默认收起，点击展开查看最新 8 条日志</n-text>
          </n-space>
          <template v-else>
            <div class="scroll-panel">
              <n-list bordered>
                <n-list-item v-for="log in visibleLogs" :key="log.id">
                  <n-space vertical size="small">
                    <n-space justify="space-between">
                      <n-tag size="small">{{ log.level }}</n-tag>
                      <n-text depth="3">{{ formatDateTime(log.createdAt) }}</n-text>
                    </n-space>
                    <n-text>{{ log.message }}</n-text>
                  </n-space>
                </n-list-item>
              </n-list>
            </div>
            <n-space v-if="canLoadMoreLogs" justify="center" style="margin-top: 12px">
              <n-button quaternary @click="loadMoreLogs">查看更早的日志</n-button>
            </n-space>
          </template>
        </n-card>
      </n-grid-item>
    </n-grid>

    <n-card title="答题记录" :bordered="false">
      <n-empty v-if="answerGroups.length === 0" description="当前任务还没有章节答题记录" />
      <n-collapse v-else>
        <n-collapse-item
          v-for="group in answerGroups"
          :key="group.key"
          :title="`${group.courseTitle} / ${group.chapterTitle}`"
          :name="group.key"
        >
          <template #header-extra>
            <n-tag size="small" type="info">{{ group.items.length }} 题</n-tag>
          </template>

          <n-data-table
            :columns="[
              { title: '题目 ID', key: 'questionId' },
              { title: '题型', key: 'questionType' },
              { title: '题目', key: 'questionTitle' },
              { title: '候选答案', key: 'candidateAnswers', render: (row: AnswerRecordItem) => row.candidateAnswers?.join(' / ') || '--' },
              { title: '答案', key: 'finalAnswer' },
              { title: '来源', key: 'answerSource' },
              { title: '置信度', key: 'confidence', render: (row: AnswerRecordItem) => formatConfidence(row.confidence) },
              { title: '决策', key: 'decision' },
              { title: '提交结果', key: 'submitResult' },
            ]"
            :data="group.items"
            :pagination="false"
          />
        </n-collapse-item>
      </n-collapse>
    </n-card>
  </n-space>
</template>

<style scoped>
.scroll-panel {
  max-height: 420px;
  overflow: auto;
  padding-right: 4px;
}
</style>
