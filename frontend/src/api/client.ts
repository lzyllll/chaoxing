import { http } from '@/api/http'
import { resolveTaskWebSocketUrl } from '@/config/runtime'
import type {
  AccountItem,
  AccountStudyConfig,
  AdminLoginPayload,
  AdminSession,
  AnswerRecordItem,
  CourseSignsResponse,
  CourseItem,
  CreateAccountPayload,
  CreateTaskPayload,
  HealthResponse,
  PendingDecisionItem,
  SignCaptchaRecognizeResponse,
  SignCaptchaResponse,
  SignCaptchaVerifyPayload,
  SignInspectResponse,
  SignPhotoUploadItem,
  SignSubmitPayload,
  SignSubmitResponse,
  SignContextPayload,
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

export async function getCourseSigns(accountId: number, courseSnapshotId: number): Promise<CourseSignsResponse> {
  const { data } = await http.get<CourseSignsResponse>(`/accounts/${accountId}/courses/${courseSnapshotId}/signs`)
  return data
}

export async function inspectSign(accountId: number, payload: SignContextPayload): Promise<SignInspectResponse> {
  const { data } = await http.post<SignInspectResponse>(`/accounts/${accountId}/signs/inspect`, payload)
  return data
}

export async function getSignCaptcha(accountId: number, payload: SignContextPayload): Promise<SignCaptchaResponse> {
  const { data } = await http.post<SignCaptchaResponse>(`/accounts/${accountId}/signs/captcha`, payload)
  return data
}

export async function recognizeSignCaptcha(
  accountId: number,
  captchaData: SignCaptchaVerifyPayload['captchaData'],
): Promise<SignCaptchaRecognizeResponse> {
  const { data } = await http.post<SignCaptchaRecognizeResponse>(`/accounts/${accountId}/signs/captcha/recognize`, {
    captchaData,
  })
  return data
}

export async function submitSign(accountId: number, payload: SignSubmitPayload): Promise<SignSubmitResponse> {
  const { data } = await http.post<SignSubmitResponse>(`/accounts/${accountId}/signs/submit`, payload)
  return data
}

export async function submitSignWithCaptcha(
  accountId: number,
  payload: SignCaptchaVerifyPayload,
): Promise<SignSubmitResponse> {
  const { data } = await http.post<SignSubmitResponse>(`/accounts/${accountId}/signs/submit-with-captcha`, payload)
  return data
}

export async function uploadSignPhoto(accountId: number, file: File): Promise<SignPhotoUploadItem> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('content_type', file.type || 'image/jpeg')
  const { data } = await http.post<SignPhotoUploadItem>(`/accounts/${accountId}/signs/photo/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
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
