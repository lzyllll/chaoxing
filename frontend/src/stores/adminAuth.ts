import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getAdminSession, loginAdmin, logoutAdmin } from '@/api/client'
import type { AdminLoginPayload, AdminSession } from '@/types'

type SessionStateTarget = {
  authEnabled: { value: boolean }
  authenticated: { value: boolean }
  initialized: { value: boolean }
  username: { value: string | null }
}

function applySessionState(session: AdminSession, target: SessionStateTarget): void {
  target.authEnabled.value = session.authEnabled
  target.authenticated.value = session.authenticated
  target.username.value = session.username ?? null
  target.initialized.value = true
}

export const useAdminAuthStore = defineStore('admin-auth', () => {
  const initialized = ref(false)
  const loading = ref(false)
  const authEnabled = ref(true)
  const authenticated = ref(false)
  const username = ref<string | null>(null)
  let pendingSessionRequest: Promise<void> | null = null

  async function fetchSession(): Promise<void> {
    const session = await getAdminSession()
    applySessionState(session, { authEnabled, authenticated, initialized, username })
  }

  async function ensureSession(): Promise<void> {
    if (initialized.value) {
      return
    }
    if (pendingSessionRequest) {
      return pendingSessionRequest
    }

    loading.value = true
    pendingSessionRequest = fetchSession()
      .catch(() => {
        authEnabled.value = true
        authenticated.value = false
        username.value = null
        initialized.value = true
      })
      .finally(() => {
        loading.value = false
        pendingSessionRequest = null
      })

    return pendingSessionRequest
  }

  async function login(payload: AdminLoginPayload): Promise<void> {
    loading.value = true
    try {
      const session = await loginAdmin(payload)
      applySessionState(session, { authEnabled, authenticated, initialized, username })
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    loading.value = true
    try {
      const session = await logoutAdmin()
      applySessionState(session, { authEnabled, authenticated, initialized, username })
    } finally {
      loading.value = false
    }
  }

  const requiresLogin = computed(() => authEnabled.value && !authenticated.value)

  return {
    authEnabled,
    authenticated,
    ensureSession,
    initialized,
    loading,
    login,
    logout,
    requiresLogin,
    username,
  }
})
