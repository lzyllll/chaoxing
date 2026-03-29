export type TaskStatus =
  | 'queued'
  | 'running'
  | 'waiting_confirmation'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type SubmissionMode = 'manual' | 'auto' | 'intelligent'

export type LowConfidenceAction = 'pause' | 'skip' | 'save_only'

export type SignType = 'normal' | 'photo' | 'qrcode' | 'location' | 'gesture' | 'signcode' | 'unknown'

export type SignResultStatus =
  | 'success'
  | 'captcha_required'
  | 'already_signed'
  | 'ended'
  | 'wrong_location'
  | 'error'

export interface HealthResponse {
  status: string
  version: string
}

export interface AdminSession {
  authEnabled: boolean
  authenticated: boolean
  username?: string | null
}

export interface AdminLoginPayload {
  username: string
  password: string
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

export interface SignLocationPayload {
  latitude: number
  longitude: number
  address: string
}

export interface SignContextPayload {
  activeId: number
  courseId: number
  classId: number
  ext?: string
  signType?: SignType | null
}

export interface SignSubmitPayload extends SignContextPayload {
  signCode?: string | null
  enc?: string | null
  location?: SignLocationPayload | null
  objectId?: string | null
  preSign?: boolean
}

export interface SignCaptchaVerifyPayload extends SignSubmitPayload {
  xPosition: number
  captchaData: SignCaptchaDataItem
}

export interface SignActivityItem {
  activeId: number
  courseId: number
  classId: number
  ext: string
  name: string
  endName: string
  activeType?: number | null
  type?: number | null
  status?: number | null
  userStatus?: number | null
  otherId: string
  signType: SignType
  isLook: boolean
  startTime?: number | null
  endTime?: number | null
}

export interface SignContextItem {
  activeId: number
  courseId: number
  classId: number
  ext: string
  signType: SignType
  name: string
}

export interface SignDetailItem {
  activeId: number
  signType: SignType
  name: string
  title?: string | null
  otherId: string
  status?: number | null
  userStatus?: number | null
  activeType?: number | null
  startTime?: number | null
  endTime?: number | null
  lateEndTime?: number | null
  signInId?: number | null
  signOutId?: number | null
  signOutPublishTime?: number | null
  numberCount?: number | null
  ifOpenAddress?: boolean | null
  ifRefreshQrcode?: boolean | null
  ifNeedVcode?: boolean | null
  locationLatitude?: number | null
  locationLongitude?: number | null
  locationRange?: number | null
  locationText?: string | null
  raw: Record<string, unknown>
}

export interface SignPreflightItem {
  activeId: number
  signType: SignType
  alreadySigned: boolean
  analysisCode?: string | null
  rawHtml: string
  detail?: SignDetailItem | null
}

export interface SignCaptchaDataItem {
  captchaId: string
  type: string
  version: string
  token: string
  captchaKey: string
  iv: string
  shadeImage: string
  cutoutImage: string
}

export interface SignSubmitResultItem {
  activeId: number
  signType: SignType
  status: SignResultStatus
  message: string
  rawResponse: string
  captchaRequired: boolean
  alreadySigned: boolean
  ended: boolean
  wrongLocation: boolean
}

export interface SignPhotoUploadItem {
  token: string
  objectId: string
  filePath: string
}

export interface CourseSignsResponse {
  course: CourseItem
  activities: SignActivityItem[]
  ext: string
}

export interface SignInspectResponse {
  context: SignContextItem
  detail: SignDetailItem
  preflight: SignPreflightItem
}

export interface SignCaptchaResponse {
  captchaData: SignCaptchaDataItem
}

export interface SignSubmitResponse {
  result: SignSubmitResultItem
  captchaData?: SignCaptchaDataItem
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
