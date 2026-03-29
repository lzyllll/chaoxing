const DEFAULT_API_BASE_URL = '/api'
const DEFAULT_WS_BASE_URL = '/ws'
const DEFAULT_API_TIMEOUT_MS = 15000

function trimTrailingSlash(value: string): string {
  if (!value) {
    return value
  }
  const trimmed = value.replace(/\/+$/, '')
  return trimmed || '/'
}

function parsePositiveInteger(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt((value || '').trim(), 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

function joinPath(basePath: string, suffix: string): string {
  const normalizedBase = trimTrailingSlash(basePath)
  return normalizedBase === '/' ? suffix : `${normalizedBase}${suffix}`
}

export const frontendRuntime = {
  apiBaseUrl: trimTrailingSlash(import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL),
  wsBaseUrl: trimTrailingSlash(import.meta.env.VITE_WS_BASE_URL?.trim() || DEFAULT_WS_BASE_URL),
  apiTimeoutMs: parsePositiveInteger(import.meta.env.VITE_API_TIMEOUT_MS, DEFAULT_API_TIMEOUT_MS),
  baiduMapAk: import.meta.env.VITE_BAIDU_MAP_AK?.trim() || '',
}

export function resolveTaskWebSocketUrl(taskId: number): string {
  const suffix = `/tasks/${taskId}`
  const baseUrl = frontendRuntime.wsBaseUrl

  if (baseUrl.startsWith('ws://') || baseUrl.startsWith('wss://')) {
    return `${trimTrailingSlash(baseUrl)}${suffix}`
  }

  if (baseUrl.startsWith('http://') || baseUrl.startsWith('https://')) {
    const url = new URL(baseUrl)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = joinPath(url.pathname, suffix)
    return url.toString()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${joinPath(baseUrl, suffix)}`
}
