import axios from 'axios'
import { frontendRuntime } from '@/config/runtime'

export const http = axios.create({
  baseURL: frontendRuntime.apiBaseUrl,
  timeout: frontendRuntime.apiTimeoutMs,
  withCredentials: true,
})
