import type {
  AccountItem,
  AccountStudyConfig,
  AnswerRecordItem,
  CourseItem,
  HealthResponse,
  PendingDecisionItem,
  TaskEventItem,
  TaskLogItem,
  TaskSummary,
} from '@/types'

const accountFixtures: AccountItem[] = [
  {
    id: 1,
    name: '主账号',
    username: '188****0001',
    status: 'active',
    lastLoginAt: '2026-03-12T08:30:00Z',
    updatedAt: '2026-03-12T08:30:00Z',
    courseCount: 6,
  },
  {
    id: 2,
    name: '备用账号',
    username: '188****0002',
    status: 'active',
    lastLoginAt: '2026-03-11T20:15:00Z',
    updatedAt: '2026-03-11T20:15:00Z',
    courseCount: 4,
  },
  {
    id: 3,
    name: '待检查账号',
    username: '188****0003',
    status: 'disabled',
    lastLoginAt: null,
    updatedAt: '2026-03-10T14:00:00Z',
    courseCount: 0,
  },
]

const taskFixtures: TaskSummary[] = [
  {
    id: 101,
    accountId: 1,
    accountName: '主账号',
    status: 'running',
    selectedCourses: ['高等数学', '大学英语'],
    progressPct: 63,
    currentCourse: '高等数学',
    currentChapter: '函数极限',
    currentJob: '视频任务点',
    errorMessage: '',
    createdAt: '2026-03-12T08:35:00Z',
    startedAt: '2026-03-12T08:36:00Z',
    finishedAt: null,
  },
  {
    id: 102,
    accountId: 2,
    accountName: '备用账号',
    status: 'waiting_confirmation',
    selectedCourses: ['计算机基础'],
    progressPct: 48,
    currentCourse: '计算机基础',
    currentChapter: '网络安全导论',
    currentJob: '章节测验',
    errorMessage: '',
    createdAt: '2026-03-12T09:10:00Z',
    startedAt: '2026-03-12T09:11:00Z',
    finishedAt: null,
  },
  {
    id: 103,
    accountId: 1,
    accountName: '主账号',
    status: 'succeeded',
    selectedCourses: ['大学英语'],
    progressPct: 100,
    currentCourse: '大学英语',
    currentChapter: 'Unit 3',
    currentJob: '阅读任务',
    errorMessage: '',
    createdAt: '2026-03-11T19:00:00Z',
    startedAt: '2026-03-11T19:02:00Z',
    finishedAt: '2026-03-11T20:06:00Z',
  },
]

function getFallbackAccount(): AccountItem {
  return accountFixtures[0]!
}

function getFallbackTask(): TaskSummary {
  return taskFixtures[0]!
}

export async function getHealth(): Promise<HealthResponse> {
  return Promise.resolve({ status: 'ok', version: '3.1.3' })
}

export async function getDashboardSummary(): Promise<{
  accountCount: number
  activeTaskCount: number
  pendingDecisionCount: number
  successRate: number
}> {
  return Promise.resolve({
    accountCount: 3,
    activeTaskCount: 2,
    pendingDecisionCount: 4,
    successRate: 92,
  })
}

export async function getAccounts(): Promise<AccountItem[]> {
  return Promise.resolve(accountFixtures)
}

export async function getAccountDetail(accountId: number): Promise<{
  account: AccountItem
  config: AccountStudyConfig
  courses: CourseItem[]
}> {
  const account = accountFixtures.find((item) => item.id === accountId) ?? getFallbackAccount()

  return Promise.resolve({
    account,
    config: {
      speed: 1.5,
      jobs: 4,
      notopenAction: 'retry',
      answerProvider: 'AI',
      submissionMode: 'intelligent',
      confidenceThreshold: 0.82,
      minCoverRate: 0.75,
      allowAiAutoSubmit: false,
      lowConfidenceAction: 'pause',
    },
    courses: [
      {
        id: 1,
        accountId: account.id,
        courseId: '210001',
        clazzId: '300001',
        cpi: '10001',
        title: '高等数学',
        teacher: '张老师',
        fetchedAt: '2026-03-12T08:31:00Z',
      },
      {
        id: 2,
        accountId: account.id,
        courseId: '210002',
        clazzId: '300002',
        cpi: '10002',
        title: '大学英语',
        teacher: '李老师',
        fetchedAt: '2026-03-12T08:31:00Z',
      },
      {
        id: 3,
        accountId: account.id,
        courseId: '210003',
        clazzId: '300003',
        cpi: '10003',
        title: '计算机基础',
        teacher: '王老师',
        fetchedAt: '2026-03-12T08:31:00Z',
      },
    ],
  })
}

export async function getTasks(): Promise<TaskSummary[]> {
  return Promise.resolve(taskFixtures)
}

export async function getTaskDetail(taskId: number): Promise<{
  task: TaskSummary
  events: TaskEventItem[]
  logs: TaskLogItem[]
  answers: AnswerRecordItem[]
}> {
  const task = taskFixtures.find((item) => item.id === taskId) ?? getFallbackTask()

  return Promise.resolve({
    task,
    events: [
      {
        id: 1,
        taskId: task.id,
        seq: 1,
        eventType: 'PROGRESS',
        createdAt: '2026-03-12T09:12:00Z',
        payload: { progressPct: 48, currentChapter: '网络安全导论' },
      },
      {
        id: 2,
        taskId: task.id,
        seq: 2,
        eventType: 'DECISION_REQUIRED',
        createdAt: '2026-03-12T09:18:00Z',
        payload: { reason: '题库覆盖率低于阈值，等待人工确认' },
      },
    ],
    logs: [
      {
        id: 1,
        taskId: task.id,
        level: 'INFO',
        message: '开始处理课程 计算机基础',
        createdAt: '2026-03-12T09:11:00Z',
      },
      {
        id: 2,
        taskId: task.id,
        level: 'WARN',
        message: '当前答题命中率不足，已暂停自动提交',
        createdAt: '2026-03-12T09:18:00Z',
      },
      {
        id: 3,
        taskId: task.id,
        level: 'INFO',
        message: '等待人工确认后继续执行',
        createdAt: '2026-03-12T09:18:10Z',
      },
    ],
    answers: [
      {
        id: 1,
        taskId: task.id,
        questionId: 'q-001',
        questionType: 'single',
        questionTitle: 'OSI 七层模型中，负责端到端通信的是哪一层？',
        finalAnswer: '传输层',
        answerSource: 'AI',
        confidence: 0.74,
        decision: 'pending_review',
        submitResult: 'manual_required',
        createdAt: '2026-03-12T09:18:00Z',
      },
      {
        id: 2,
        taskId: task.id,
        questionId: 'q-002',
        questionType: 'multiple',
        questionTitle: '以下哪些属于常见网络攻击？',
        finalAnswer: 'SQL 注入；XSS',
        answerSource: '题库',
        confidence: 0.91,
        decision: 'accepted',
        submitResult: 'auto_submitted',
        createdAt: '2026-03-12T09:17:00Z',
      },
    ],
  })
}

export async function getPendingDecisions(): Promise<PendingDecisionItem[]> {
  return Promise.resolve([
    {
      id: 1,
      taskId: 102,
      answerRecordId: 1,
      reason: '置信度低于 0.80，已暂停自动提交',
      status: 'pending',
      createdAt: '2026-03-12T09:18:00Z',
    },
    {
      id: 2,
      taskId: 104,
      answerRecordId: 8,
      reason: '题库覆盖率低于 75%',
      status: 'pending',
      createdAt: '2026-03-12T08:50:00Z',
    },
  ])
}
