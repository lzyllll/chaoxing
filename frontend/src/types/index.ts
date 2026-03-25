export type TaskStatus =
  | 'queued'
  | 'running'
  | 'waiting_confirmation'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type SubmissionMode = 'manual' | 'auto' | 'intelligent'

export type LowConfidenceAction = 'pause' | 'skip' | 'save_only'

export interface HealthResponse {
  status: string
  version: string
}

export interface AccountItem {
  id: number
  name: string
  username: string
  passwordEncrypted?: string
  cookiesPath?: string
  status: 'active' | 'disabled'
  lastLoginAt?: string | null
  updatedAt: string
  courseCount: number
}

export interface AccountStudyConfig {
  speed: number
  jobs: number
  notopenAction: string
  answerProvider: string
  submissionMode: SubmissionMode
  confidenceThreshold: number
  minCoverRate: number
  allowAiAutoSubmit: boolean
  lowConfidenceAction: LowConfidenceAction
  providerConfigJson?: string
}

export interface CourseItem {
  id: number
  accountId: number
  courseId: string
  clazzId: string
  cpi: string
  title: string
  teacher: string
  fetchedAt: string
}

export interface TaskSummary {
  id: number
  accountId: number
  accountName: string
  status: TaskStatus
  selectedCourses: string[]
  progressPct: number
  currentCourse: string
  currentChapter: string
  currentJob: string
  errorMessage: string
  createdAt: string
  startedAt?: string | null
  finishedAt?: string | null
}

export interface TaskEventItem {
  id: number
  taskId: number
  seq: number
  eventType: string
  createdAt: string
  payload: Record<string, unknown>
}

export interface TaskLogItem {
  id: number
  taskId: number
  level: string
  message: string
  createdAt: string
}

export interface AnswerRecordItem {
  id: number
  taskId: number
  courseTitle?: string
  chapterTitle?: string
  questionId: string
  questionType: string
  questionTitle: string
  options?: string[]
  candidateAnswers?: string[]
  finalAnswer: string
  answerSource: string
  confidence: number
  decision: string
  submitResult: string
  createdAt: string
}

export interface PendingDecisionItem {
  id: number
  taskId: number
  answerRecordId: number
  reason: string
  status: string
  createdAt: string
}

export interface CreateAccountPayload {
  name: string
  username: string
  passwordEncrypted?: string
  cookiesPath?: string
  status?: 'active' | 'disabled'
}

export interface CreateTaskPayload {
  accountId: number
  selectedCourses: string[]
}

export interface UpdateAccountPayload extends CreateAccountPayload {
  config: AccountStudyConfig
}
