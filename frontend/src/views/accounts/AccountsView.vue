<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NPopconfirm, NSpace, NTag, useMessage } from 'naive-ui'

import { createAccount, deleteAccount, getAccounts } from '@/api/client'
import type { AccountItem, CreateAccountPayload } from '@/types'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const message = useMessage()

const loading = ref(true)
const submitting = ref(false)
const deletingAccountId = ref<number | null>(null)
const accounts = ref<AccountItem[]>([])
const showCreateModal = ref(false)

const form = ref<CreateAccountPayload>({
  name: '',
  username: '',
  passwordEncrypted: '',
  cookiesPath: '',
  status: 'active',
})

const columns = computed(() => [
  { title: 'ID', key: 'id' },
  { title: '名称', key: 'name' },
  { title: '账号', key: 'username' },
  { title: '状态', key: 'status' },
  { title: '课程数', key: 'courseCount' },
  {
    title: '最近登录',
    key: 'lastLoginAt',
    render: (row: AccountItem) => formatDateTime(row.lastLoginAt),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: AccountItem) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              secondary: true,
              onClick: () => openAccount(row.id),
            },
            { default: () => '查看' },
          ),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDeleteAccount(row),
            },
            {
              trigger: () =>
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error',
                    ghost: true,
                    loading: deletingAccountId.value === row.id,
                  },
                  { default: () => '删除' },
                ),
              default: () => `删除账号“${row.name}”及其历史任务？`,
            },
          ),
        ],
      }),
  },
])

async function loadAccounts(): Promise<void> {
  loading.value = true
  try {
    accounts.value = await getAccounts()
  } catch (error) {
    message.error('加载账号列表失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadAccounts()
})

function openAccount(accountId: number): void {
  void router.push(`/accounts/${accountId}`)
}

function resetForm(): void {
  form.value = {
    name: '',
    username: '',
    passwordEncrypted: '',
    cookiesPath: '',
    status: 'active',
  }
}

function openCreateModal(): void {
  resetForm()
  showCreateModal.value = true
}

async function handleDeleteAccount(account: AccountItem): Promise<void> {
  deletingAccountId.value = account.id
  try {
    await deleteAccount(account.id)
    message.success('账号已删除')
    await loadAccounts()
  } catch (error: unknown) {
    const maybeAxiosError = error as { response?: { status?: number; data?: { detail?: string } } }
    if (maybeAxiosError?.response?.status === 409) {
      message.error(maybeAxiosError.response.data?.detail ?? '该账号还有运行中的任务，不能删除')
    } else {
      message.error('删除账号失败')
    }
  } finally {
    deletingAccountId.value = null
  }
}

async function submitCreateAccount(): Promise<void> {
  const name = (form.value.name ?? '').trim()
  const username = (form.value.username ?? '').trim()

  if (!name || !username) {
    message.warning('请填写名称和账号')
    return
  }

  submitting.value = true
  try {
    await createAccount({
      name,
      username,
      passwordEncrypted: form.value.passwordEncrypted?.trim() || '',
      cookiesPath: form.value.cookiesPath?.trim() || undefined,
      status: form.value.status ?? 'active',
    })
    message.success('账号新增成功')
    showCreateModal.value = false
    await loadAccounts()
  } catch (error: unknown) {
    const maybeAxiosError = error as { response?: { status?: number } }
    if (maybeAxiosError?.response?.status === 409) {
      message.error('该账号已存在')
    } else {
      message.error('新增账号失败，请稍后重试')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <n-space vertical size="large">
    <n-card :bordered="false" title="账号列表">
      <template #header-extra>
        <n-button type="primary" @click="openCreateModal">新增账号</n-button>
      </template>
      <n-data-table :loading="loading" :columns="columns" :data="accounts" :pagination="false">
        <template #empty>
          暂无账号
        </template>
      </n-data-table>
    </n-card>

    <n-grid x-gap="16" cols="1 l:3" responsive="screen">
      <n-grid-item v-for="item in accounts" :key="item.id">
        <n-card hoverable :bordered="false" @click="openAccount(item.id)">
          <n-space vertical size="small">
            <n-text strong>{{ item.name }}</n-text>
            <n-text depth="3">{{ item.username }}</n-text>
            <n-space justify="space-between">
              <n-tag :type="item.status === 'active' ? 'success' : 'warning'">
                {{ item.status }}
              </n-tag>
              <n-text depth="3">{{ item.courseCount }} 门课程</n-text>
            </n-space>
            <n-space justify="end">
              <n-popconfirm @positive-click="handleDeleteAccount(item)">
                <template #trigger>
                  <n-button
                    size="small"
                    type="error"
                    ghost
                    :loading="deletingAccountId === item.id"
                    @click.stop
                  >
                    删除
                  </n-button>
                </template>
                删除账号“{{ item.name }}”及其历史任务？
              </n-popconfirm>
            </n-space>
          </n-space>
        </n-card>
      </n-grid-item>
    </n-grid>

    <n-modal v-model:show="showCreateModal" preset="card" title="新增账号" style="width: 520px">
      <n-space vertical>
        <n-input v-model:value="form.name" placeholder="账号名称（例如：主账号）" />
        <n-input v-model:value="form.username" placeholder="账号（手机号/学号）" />
        <n-input v-model:value="form.passwordEncrypted" placeholder="密码（可留空）" type="password" show-password-on="click" />
        <n-input v-model:value="form.cookiesPath" placeholder="Cookies 文件路径（可留空）" />
        <n-space justify="end">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="submitCreateAccount">提交</n-button>
        </n-space>
      </n-space>
    </n-modal>
  </n-space>
</template>
