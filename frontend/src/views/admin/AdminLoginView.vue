<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NForm, NFormItem, NIcon, NInput, NText, useMessage } from 'naive-ui'
import { LockClosedOutline, PersonOutline, ShieldCheckmarkOutline } from '@vicons/ionicons5'

import { useAdminAuthStore } from '@/stores/adminAuth'

const authStore = useAdminAuthStore()
const route = useRoute()
const router = useRouter()
const message = useMessage()

const form = reactive({
  username: '',
  password: '',
})

function getRedirectTarget(): string {
  const redirect = route.query.redirect
  return typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/'
}

function getErrorMessage(error: unknown, fallback: string): string {
  const maybeAxiosError = error as { response?: { data?: { detail?: string } } }
  return maybeAxiosError.response?.data?.detail ?? fallback
}

async function submitLogin(): Promise<void> {
  const username = form.username.trim()
  if (!username || !form.password) {
    message.warning('请输入管理员账号和密码')
    return
  }

  try {
    await authStore.login({
      username,
      password: form.password,
    })
    form.password = ''
    await router.replace(getRedirectTarget())
  } catch (error: unknown) {
    message.error(getErrorMessage(error, '登录失败，请检查管理员账号和密码'))
  }
}
</script>

<template>
  <div class="admin-login">
    <div class="admin-login__panel">
      <div class="admin-login__intro">
        <div class="admin-login__badge">
          <n-icon size="22">
            <ShieldCheckmarkOutline />
          </n-icon>
        </div>
        <span>管理员访问控制</span>
      </div>

      <h1>Chaoxing Web 控制台</h1>
      <p>登录后才能访问账号管理、任务调度和实时任务流。</p>

      <n-card class="admin-login__card" :bordered="false">
        <n-form @submit.prevent="submitLogin">
          <n-form-item label="管理员账号">
            <n-input v-model:value="form.username" placeholder="在 backend.ini 的 [admin] 中配置" clearable>
              <template #prefix>
                <n-icon>
                  <PersonOutline />
                </n-icon>
              </template>
            </n-input>
          </n-form-item>

          <n-form-item label="管理员密码">
            <n-input
              v-model:value="form.password"
              type="password"
              show-password-on="click"
              placeholder="输入配置中的管理员密码"
              @keydown.enter.prevent="submitLogin"
            >
              <template #prefix>
                <n-icon>
                  <LockClosedOutline />
                </n-icon>
              </template>
            </n-input>
          </n-form-item>

          <n-button type="primary" block size="large" :loading="authStore.loading" @click="submitLogin">
            登录控制台
          </n-button>
        </n-form>

        <n-text depth="3" class="admin-login__hint">
          未配置 `[admin].username` 和 `[admin].password` 时，将保持当前免登录模式。
        </n-text>
      </n-card>
    </div>
  </div>
</template>

<style scoped>
.admin-login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(14, 165, 233, 0.18), transparent 34%),
    radial-gradient(circle at bottom right, rgba(245, 158, 11, 0.2), transparent 30%),
    linear-gradient(160deg, #f8fbff 0%, #eef4ff 48%, #f8fafc 100%);
}

.admin-login__panel {
  width: min(100%, 440px);
}

.admin-login__intro {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  padding: 8px 14px 8px 10px;
  border: 1px solid rgba(14, 165, 233, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: #0369a1;
  font-size: 14px;
  font-weight: 600;
}

.admin-login__badge {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #0f766e, #0284c7);
  color: #fff;
}

.admin-login h1 {
  margin: 0 0 10px;
  color: #0f172a;
  font-size: 36px;
  line-height: 1.05;
}

.admin-login p {
  margin: 0 0 24px;
  color: #475569;
  font-size: 15px;
}

.admin-login__card {
  border-radius: 24px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.admin-login__hint {
  display: block;
  margin-top: 18px;
}
</style>
