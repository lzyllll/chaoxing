import { http } from '@/api/http'
import type {
  AccountItem,
  AccountStudyConfig,
  AnswerRecordItem,
  CourseItem,
  CreateAccountPayload,
  CreateTaskPayload,
  HealthResponse,
  PendingDecisionItem,
  TaskEventItem,
  TaskLogItem,
  TaskSummary,
} from '@/types'

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>('/health')
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

export async function getPendingDecisions(): Promise<PendingDecisionItem[]> {
  const { data } = await http.get<PendingDecisionItem[]>('/decisions')
  return data
}

export function createTaskWebSocket(taskId: number): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(`${protocol}//${window.location.host}/ws/tasks/${taskId}`)
}
