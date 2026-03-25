import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'
import { defineConfig, loadEnv } from 'vite'

function isRelativeRoute(value: string): boolean {
  return value.startsWith('/')
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const devHost = env.VITE_DEV_HOST || '127.0.0.1'
  const devPort = Number.parseInt(env.VITE_DEV_PORT || '5173', 10)
  const apiBaseUrl = (env.VITE_API_BASE_URL || '/api').trim()
  const wsBaseUrl = (env.VITE_WS_BASE_URL || '/ws').trim()
  const proxyTarget = (env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000').trim()
  const proxy: Record<string, { target: string; changeOrigin: boolean; ws?: boolean }> = {}

  if (isRelativeRoute(apiBaseUrl)) {
    proxy[apiBaseUrl] = {
      target: proxyTarget,
      changeOrigin: true,
    }
  }

  if (isRelativeRoute(wsBaseUrl)) {
    proxy[wsBaseUrl] = {
      target: proxyTarget,
      changeOrigin: true,
      ws: true,
    }
  }

  return {
    plugins: [
      vue(),
      AutoImport({
        imports: ['vue', 'vue-router'],
        dts: 'src/auto-imports.d.ts',
      }),
      Components({
        resolvers: [NaiveUiResolver()],
        dts: 'src/components.d.ts',
      }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: devHost,
      port: Number.isFinite(devPort) ? devPort : 5173,
      proxy,
    },
  }
})
