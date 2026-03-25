<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'

import { getAccountDetail, syncAccountCourses, updateAccount } from '@/api/client'
import type { AccountItem, AccountStudyConfig, CourseItem, UpdateAccountPayload } from '@/types'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const message = useMessage()

const loading = ref(true)
const saving = ref(false)
const syncingCourses = ref(false)

const account = ref<AccountItem | null>(null)
const config = ref<AccountStudyConfig | null>(null)
const courses = ref<CourseItem[]>([])

const accountId = computed(() => Number(route.params.id))

async function loadDetail(): Promise<void> {
  loading.value = true
  try {
    const detail = await getAccountDetail(accountId.value)
    account.value = detail.account
    config.value = {
      ...detail.config,
      providerConfigJson: detail.config.providerConfigJson ?? '{}',
    }
    courses.value = detail.courses
  } finally {
    loading.value = false
  }
}

async function saveAccount(): Promise<void> {
  if (!account.value || !config.value) {
    return
  }

  saving.value = true
  try {
    const payload: UpdateAccountPayload = {
      name: account.value.name.trim(),
      username: account.value.username.trim(),
      passwordEncrypted: account.value.passwordEncrypted?.trim() || '',
      cookiesPath: account.value.cookiesPath?.trim() || undefined,
      status: account.value.status,
      config: {
        ...config.value,
        speed: config.value.speed ?? 1,
        jobs: config.value.jobs ?? 4,
        confidenceThreshold: config.value.confidenceThreshold ?? 0.8,
        minCoverRate: config.value.minCoverRate ?? 0.7,
        providerConfigJson: config.value.providerConfigJson?.trim() || '{}',
      },
    }
    const detail = await updateAccount(accountId.value, payload)
    account.value = detail.account
    config.value = {
      ...detail.config,
      providerConfigJson: detail.config.providerConfigJson ?? '{}',
    }
    courses.value = detail.courses
    message.success('账号配置已保存')
  } catch (error: unknown) {
    const maybeAxiosError = error as { response?: { status?: number } }
    if (maybeAxiosError?.response?.status === 409) {
      message.error('该账号已存在')
    } else {
      message.error('保存失败，请检查输入内容')
    }
  } finally {
    saving.value = false
  }
}

async function refreshCourses(): Promise<void> {
  syncingCourses.value = true
  try {
    const response = await syncAccountCourses(accountId.value)
    account.value = response.detail.account
    config.value = {
      ...response.detail.config,
      providerConfigJson: response.detail.config.providerConfigJson ?? '{}',
    }
    courses.value = response.detail.courses
    message.success(`课程同步完成，已获取 ${response.summary.courseCount} 门课程`)
  } catch (error) {
    message.error('课程同步失败，请检查 cookies 或账号密码')
  } finally {
    syncingCourses.value = false
  }
}

onMounted(async () => {
  await loadDetail()
})
</script>

<template>
  <n-space vertical size="large">
    <n-grid x-gap="16" y-gap="16" cols="1 l:2" responsive="screen">
      <n-grid-item>
        <n-card :bordered="false" :loading="loading" title="账号信息">
          <n-form v-if="account" label-placement="top">
            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="账号名称">
                  <n-input v-model:value="account.name" placeholder="例如：主账号" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="账号状态">
                  <n-select
                    v-model:value="account.status"
                    :options="[
                      { label: '启用', value: 'active' },
                      { label: '停用', value: 'disabled' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-form-item label="超星账号">
              <n-input v-model:value="account.username" placeholder="手机号 / 学号" />
            </n-form-item>
            <n-form-item label="密码">
              <n-input
                v-model:value="account.passwordEncrypted"
                type="password"
                show-password-on="click"
                placeholder="可留空，仅依赖 cookies 登录"
              />
            </n-form-item>
            <n-form-item label="Cookies 路径">
              <n-input v-model:value="account.cookiesPath" placeholder="留空则写入后端 accounts_dir/用户名.json" />
            </n-form-item>

            <n-space justify="space-between">
              <n-text depth="3">
                最近登录：{{ formatDateTime(account.lastLoginAt) }}
              </n-text>
              <n-space>
                <n-button :loading="syncingCourses" @click="refreshCourses">同步课程</n-button>
                <n-button type="primary" :loading="saving" @click="saveAccount">保存配置</n-button>
              </n-space>
            </n-space>
          </n-form>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card :bordered="false" :loading="loading" title="刷课策略">
          <n-form v-if="config" label-placement="top">
            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="视频倍速">
                  <n-input-number v-model:value="config.speed" :min="1" :max="2" :step="0.1" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="章节并发数">
                  <n-input-number v-model:value="config.jobs" :min="1" :max="8" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="未开放章节处理">
                  <n-select
                    v-model:value="config.notopenAction"
                    :options="[
                      { label: '重试', value: 'retry' },
                      { label: '跳过', value: 'continue' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="答题提交模式">
                  <n-select
                    v-model:value="config.submissionMode"
                    :options="[
                      { label: '智能提交', value: 'intelligent' },
                      { label: '自动提交', value: 'auto' },
                      { label: '仅保存不交卷', value: 'manual' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="答题 Provider">
                  <n-input v-model:value="config.answerProvider" placeholder="如 AI / SiliconFlow / 留空沿用 backend.ini 的 [tiku]" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="低置信度动作">
                  <n-select
                    v-model:value="config.lowConfidenceAction"
                    :options="[
                      { label: '暂停等待人工', value: 'pause' },
                      { label: '跳过', value: 'skip' },
                      { label: '仅保存', value: 'save_only' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="置信度阈值">
                  <n-input-number v-model:value="config.confidenceThreshold" :min="0" :max="1" :step="0.05" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="最低覆盖率">
                  <n-input-number v-model:value="config.minCoverRate" :min="0" :max="1" :step="0.05" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-form-item label="Provider 附加配置(JSON)">
              <n-input
                v-model:value="config.providerConfigJson"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 8 }"
                placeholder='{"token":"...","base_url":"..."}'
              />
            </n-form-item>

            <n-checkbox v-model:checked="config.allowAiAutoSubmit">
              允许 AI 答案自动提交
            </n-checkbox>
          </n-form>
        </n-card>
      </n-grid-item>
    </n-grid>

    <n-card :bordered="false" :loading="loading" title="课程快照">
      <template #header-extra>
        <n-tag type="info">{{ courses.length }} 门课程</n-tag>
      </template>

      <n-data-table
        :columns="[
          { title: '课程名', key: 'title' },
          { title: '教师', key: 'teacher' },
          { title: '课程 ID', key: 'courseId' },
          { title: '班级 ID', key: 'clazzId' },
          { title: '同步时间', key: 'fetchedAt', render: (row: CourseItem) => formatDateTime(row.fetchedAt) },
        ]"
        :data="courses"
        :pagination="false"
      >
        <template #empty>
          请先点击“同步课程”拉取该账号的课程列表
        </template>
      </n-data-table>
    </n-card>
  </n-space>
</template>
