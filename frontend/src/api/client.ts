import { http } from '@/api/http'
import { resolveTaskWebSocketUrl } from '@/config/runtime'
import type {
  AccountItem,
  AccountStudyConfig,
  AdminLoginPayload,
  AdminSession,
  AnswerRecordItem,
  CourseItem,
  CreateAccountPayload,
  CreateTaskPayload,
  HealthResponse,
  PendingDecisionItem,
  TaskEventItem,
  TaskLogItem,
  TaskSummary,
  UpdateAccountPayload,
} from '@/types'

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>('/health')
  return data
}

export async function getAdminSession(): Promise<AdminSession> {
  const { data } = await http.get<AdminSession>('/admin/session')
  return data
}

export async function loginAdmin(payload: AdminLoginPayload): Promise<AdminSession> {
  const { data } = await http.post<AdminSession>('/admin/login', payload)
  return data
}

export async function logoutAdmin(): Promise<AdminSession> {
  const { data } = await http.post<AdminSession>('/admin/logout')
  return data
}

export async function getDashboardSummary(): Promise<{
  accountCount: number
  activeTaskCount: number
  pendingDecisionCount: number
  successRate: number
}> {
  const { data } = await http.get('/dashboard/summary')
  return data
}

export async function getAccounts(): Promise<AccountItem[]> {
  const { data } = await http.get<AccountItem[]>('/accounts')
  return data
}

export async function createAccount(payload: CreateAccountPayload): Promise<AccountItem> {
  const { data } = await http.post<AccountItem>('/accounts', payload)
  return data
}

export async function getAccountDetail(accountId: number): Promise<{
  account: AccountItem
  config: AccountStudyConfig
  courses: CourseItem[]
}> {
  const { data } = await http.get(`/accounts/${accountId}`)
  return data
}

export async function updateAccount(
  accountId: number,
  payload: UpdateAccountPayload,
): Promise<{
  account: AccountItem
  config: AccountStudyConfig
  courses: CourseItem[]
}> {
  const { data } = await http.put(`/accounts/${accountId}`, payload)
  return data
}

export async function syncAccountCourses(accountId: number): Promise<{
  summary: {
    accountId: number
    courseCount: number
    fetchedAt?: string | null
  }
  detail: {
    account: AccountItem
    config: AccountStudyConfig
    courses: CourseItem[]
  }
}> {
  const { data } = await http.post(`/accounts/${accountId}/sync-courses`)
  return data
}

export async function deleteAccount(accountId: number): Promise<void> {
  await http.delete(`/accounts/${accountId}`)
}

export async function getTasks(): Promise<TaskSummary[]> {
  const { data } = await http.get<TaskSummary[]>('/tasks')
  return data
}

export async function createTask(payload: CreateTaskPayload): Promise<TaskSummary> {
  const { data } = await http.post<TaskSummary>('/tasks', payload)
  return data
}

export async function getTaskDetail(taskId: number): Promise<{
  task: TaskSummary
  events: TaskEventItem[]
  logs: TaskLogItem[]
  answers: AnswerRecordItem[]
}> {
  const { data } = await http.get(`/tasks/${taskId}`)
  return data
}

export async function deleteTask(taskId: number): Promise<void> {
  await http.delete(`/tasks/${taskId}`)
}

export async function getPendingDecisions(): Promise<PendingDecisionItem[]> {
  const { data } = await http.get<PendingDecisionItem[]>('/decisions')
  return data
}

export function createTaskWebSocket(taskId: number): WebSocket {
  return new WebSocket(resolveTaskWebSocketUrl(taskId))
}
