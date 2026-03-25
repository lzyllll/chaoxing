<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'

import { createTask, getAccountDetail, getAccounts, syncAccountCourses } from '@/api/client'
import type { AccountItem, CourseItem } from '@/types'

const router = useRouter()
const message = useMessage()

const loading = ref(true)
const courseLoading = ref(false)
const submitting = ref(false)
const syncingCourses = ref(false)

const accounts = ref<AccountItem[]>([])
const selectedAccountId = ref<number | null>(null)
const selectedCourses = ref<string[]>([])
const courseOptions = ref<Array<{ label: string; value: string }>>([])

const accountOptions = computed(() =>
  accounts.value.map((item) => ({
    label: `${item.name}（${item.username}）`,
    value: item.id,
  })),
)

const canSubmit = computed(() => selectedAccountId.value !== null && selectedCourses.value.length > 0)

async function loadAccounts(): Promise<void> {
  loading.value = true
  try {
    accounts.value = await getAccounts()
    selectedAccountId.value = accounts.value[0]?.id ?? null
  } catch (error) {
    message.error('加载账号列表失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

async function loadCourses(accountId: number): Promise<void> {
  courseLoading.value = true
  try {
    const detail = await getAccountDetail(accountId)
    courseOptions.value = detail.courses.map((course: CourseItem) => ({
      label: `${course.title}${course.teacher ? ` · ${course.teacher}` : ''}`,
      value: course.courseId,
    }))
  } catch (error) {
    courseOptions.value = []
    message.error('加载课程列表失败，请稍后重试')
  } finally {
    courseLoading.value = false
  }
}

async function refreshSelectedAccountCourses(): Promise<void> {
  if (selectedAccountId.value === null) {
    message.warning('请先选择账号')
    return
  }

  syncingCourses.value = true
  try {
    const response = await syncAccountCourses(selectedAccountId.value)
    courseOptions.value = response.detail.courses.map((course: CourseItem) => ({
      label: `${course.title}${course.teacher ? ` · ${course.teacher}` : ''}`,
      value: course.courseId,
    }))
    message.success(`同步完成，共获取 ${response.summary.courseCount} 门课程`)
  } catch (error) {
    message.error('同步课程失败，请检查该账号是否可登录')
  } finally {
    syncingCourses.value = false
  }
}

async function submitTask(): Promise<void> {
  if (selectedAccountId.value === null) {
    message.warning('请先选择账号')
    return
  }

  if (selectedCourses.value.length === 0) {
    message.warning('请至少选择一门课程')
    return
  }

  submitting.value = true
  try {
    const task = await createTask({
      accountId: selectedAccountId.value,
      selectedCourses: selectedCourses.value,
    })
    message.success('任务创建成功')
    void router.push(`/tasks/${task.id}`)
  } catch (error: unknown) {
    const maybeAxiosError = error as { response?: { status?: number } }
    if (maybeAxiosError?.response?.status === 404) {
      message.error('账号不存在，请刷新后重试')
    } else if (maybeAxiosError?.response?.status === 400) {
      message.error('任务创建失败，请先同步课程并至少选择一门课程')
    } else {
      message.error('创建任务失败，请稍后重试')
    }
  } finally {
    submitting.value = false
  }
}

watch(selectedAccountId, async (accountId) => {
  selectedCourses.value = []
  if (accountId === null) {
    courseOptions.value = []
    return
  }
  await loadCourses(accountId)
})

onMounted(async () => {
  await loadAccounts()
})
</script>

<template>
  <n-grid x-gap="16" y-gap="16" cols="1 l:2" responsive="screen">
    <n-grid-item>
      <n-card title="创建刷课任务" :bordered="false" :loading="loading">
        <n-form label-placement="top">
          <n-form-item label="选择账号">
            <n-select v-model:value="selectedAccountId" :options="accountOptions" placeholder="请选择账号" />
          </n-form-item>
          <n-form-item label="选择课程">
            <n-spin :show="courseLoading">
              <n-space justify="space-between" style="margin-bottom: 12px">
                <n-text depth="3">支持多选课程，按所选顺序依次执行</n-text>
                <n-button text type="primary" :loading="syncingCourses" @click="refreshSelectedAccountCourses">
                  重新同步课程
                </n-button>
              </n-space>
              <n-checkbox-group v-model:value="selectedCourses">
                <n-space vertical>
                  <n-checkbox v-for="option in courseOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </n-checkbox>
                </n-space>
              </n-checkbox-group>
            </n-spin>
          </n-form-item>
          <n-form-item label="任务说明">
            <n-input type="textarea" placeholder="可填写本次任务备注、答题策略或特殊说明" />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submitTask">启动任务</n-button>
            <n-button>保存为模板</n-button>
          </n-space>
        </n-form>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card title="执行策略" :bordered="false">
        <n-alert type="info" show-icon>
          当前页面会直接创建后台刷课任务，并在详情页通过 WebSocket 查看视频进度与答题情况。
        </n-alert>
        <n-list bordered style="margin-top: 16px">
          <n-list-item>支持多账号独立配置 cookies 与答题策略</n-list-item>
          <n-list-item>课程通过复选框勾选后统一创建任务</n-list-item>
          <n-list-item>可配置人工确认 / 智能提交 / 全自动提交</n-list-item>
          <n-list-item>创建后会自动跳转任务详情页并继续订阅 WebSocket</n-list-item>
        </n-list>
      </n-card>
    </n-grid-item>
  </n-grid>
</template>
