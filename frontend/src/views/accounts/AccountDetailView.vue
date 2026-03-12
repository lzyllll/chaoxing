<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { getAccountDetail } from '@/api/client'
import type { AccountItem, AccountStudyConfig, CourseItem } from '@/types'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const loading = ref(true)
const account = ref<AccountItem | null>(null)
const config = ref<AccountStudyConfig | null>(null)
const courses = ref<CourseItem[]>([])

const accountId = computed(() => Number(route.params.id))

onMounted(async () => {
  const detail = await getAccountDetail(accountId.value)
  account.value = detail.account
  config.value = detail.config
  courses.value = detail.courses
  loading.value = false
})
</script>

<template>
  <n-space vertical size="large">
    <n-card :bordered="false" :loading="loading" title="账号概览">
      <n-descriptions v-if="account" label-placement="top" bordered :column="4">
        <n-descriptions-item label="账号名称">{{ account.name }}</n-descriptions-item>
        <n-descriptions-item label="登录账号">{{ account.username }}</n-descriptions-item>
        <n-descriptions-item label="状态">{{ account.status }}</n-descriptions-item>
        <n-descriptions-item label="最近登录">
          {{ formatDateTime(account.lastLoginAt) }}
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <n-grid x-gap="16" y-gap="16" cols="1 l:2" responsive="screen">
      <n-grid-item>
        <n-card :bordered="false" :loading="loading" title="学习配置">
          <n-descriptions v-if="config" label-placement="left" bordered :column="1">
            <n-descriptions-item label="倍速">{{ config.speed }}</n-descriptions-item>
            <n-descriptions-item label="并发章节数">{{ config.jobs }}</n-descriptions-item>
            <n-descriptions-item label="关闭任务点处理">{{ config.notopenAction }}</n-descriptions-item>
            <n-descriptions-item label="答题来源">{{ config.answerProvider }}</n-descriptions-item>
            <n-descriptions-item label="提交模式">{{ config.submissionMode }}</n-descriptions-item>
            <n-descriptions-item label="置信度阈值">{{ config.confidenceThreshold }}</n-descriptions-item>
            <n-descriptions-item label="最低覆盖率">{{ config.minCoverRate }}</n-descriptions-item>
            <n-descriptions-item label="允许 AI 自动提交">
              {{ config.allowAiAutoSubmit ? '是' : '否' }}
            </n-descriptions-item>
            <n-descriptions-item label="低置信度动作">
              {{ config.lowConfidenceAction }}
            </n-descriptions-item>
          </n-descriptions>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card :bordered="false" :loading="loading" title="课程快照">
          <n-list bordered>
            <n-list-item v-for="course in courses" :key="course.id">
              <n-space vertical size="small">
                <n-text strong>{{ course.title }}</n-text>
                <n-text depth="3">教师：{{ course.teacher || '未知' }}</n-text>
                <n-text depth="3">课程 ID：{{ course.courseId }} / clazz_id：{{ course.clazzId }}</n-text>
              </n-space>
            </n-list-item>
          </n-list>
        </n-card>
      </n-grid-item>
    </n-grid>
  </n-space>
</template>
