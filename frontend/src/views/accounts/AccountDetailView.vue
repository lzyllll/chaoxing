<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'

import { getAccountDetail, syncAccountCourses, updateAccount } from '@/api/client'
import type { AccountItem, AccountStudyConfig, CourseItem, UpdateAccountPayload } from '@/types'
import { formatDateTime } from '@/utils/format'

type ProviderKey = 'TikuYanxi' | 'TikuLike' | 'TikuAdapter' | 'AI' | 'SiliconFlow'
type ProviderMode = 'single' | 'chain'
type ProviderConfigValue = string | number | boolean
type ProviderFieldType = 'input' | 'password' | 'number' | 'switch'

interface ProviderFieldDef {
  key: string
  label: string
  type: ProviderFieldType
  placeholder?: string
  min?: number
  max?: number
  step?: number
  defaultValue?: ProviderConfigValue
}

interface ProviderNode {
  id: number
  provider: ProviderKey | null
  config: Record<string, ProviderConfigValue>
}

const PROVIDER_OPTIONS: Array<{ label: string; value: ProviderKey }> = [
  { label: 'TikuYanxi', value: 'TikuYanxi' },
  { label: 'TikuLike', value: 'TikuLike' },
  { label: 'TikuAdapter', value: 'TikuAdapter' },
  { label: 'AI', value: 'AI' },
  { label: 'SiliconFlow', value: 'SiliconFlow' },
]

const PROVIDER_FIELD_MAP: Record<ProviderKey, ProviderFieldDef[]> = {
  TikuYanxi: [
    {
      key: 'tokens',
      label: 'Tokens',
      type: 'password',
      placeholder: '多个 token 用英文逗号分隔',
    },
  ],
  TikuLike: [
    {
      key: 'tokens',
      label: 'Tokens',
      type: 'password',
      placeholder: '多个 token 用英文逗号分隔',
    },
    {
      key: 'likeapi_model',
      label: '模型',
      type: 'input',
      placeholder: '如 glm-4.5-air',
    },
    {
      key: 'likeapi_retry_times',
      label: '重试次数',
      type: 'number',
      min: 1,
      step: 1,
      defaultValue: 3,
    },
    {
      key: 'likeapi_search',
      label: '联网搜索',
      type: 'switch',
      defaultValue: false,
    },
    {
      key: 'likeapi_vision',
      label: '视觉识别',
      type: 'switch',
      defaultValue: true,
    },
    {
      key: 'likeapi_retry',
      label: '自动重试',
      type: 'switch',
      defaultValue: true,
    },
  ],
  TikuAdapter: [
    {
      key: 'url',
      label: '接口地址',
      type: 'input',
      placeholder: 'TikuAdapter 服务地址',
    },
  ],
  AI: [
    {
      key: 'endpoint',
      label: 'Endpoint',
      type: 'input',
      placeholder: '如 https://example.com/v1',
    },
    {
      key: 'key',
      label: 'API Key',
      type: 'password',
      placeholder: '输入兼容 OpenAI 的 API Key',
    },
    {
      key: 'model',
      label: '模型',
      type: 'input',
      placeholder: '如 gpt-5.4',
    },
    {
      key: 'http_proxy',
      label: 'HTTP Proxy',
      type: 'input',
      placeholder: '可选，如 http://127.0.0.1:7890',
    },
    {
      key: 'min_interval_seconds',
      label: '最小请求间隔（秒）',
      type: 'number',
      min: 0,
      step: 1,
      defaultValue: 3,
    },
  ],
  SiliconFlow: [
    {
      key: 'siliconflow_key',
      label: 'API Key',
      type: 'password',
      placeholder: '硅基流动 API Key',
    },
    {
      key: 'siliconflow_model',
      label: '模型',
      type: 'input',
      placeholder: '如 deepseek-ai/DeepSeek-V3',
      defaultValue: 'deepseek-ai/DeepSeek-V3',
    },
    {
      key: 'siliconflow_endpoint',
      label: 'Endpoint',
      type: 'input',
      placeholder: '默认官方 chat completions 地址',
      defaultValue: 'https://api.siliconflow.cn/v1/chat/completions',
    },
    {
      key: 'min_interval_seconds',
      label: '最小请求间隔（秒）',
      type: 'number',
      min: 0,
      step: 1,
      defaultValue: 3,
    },
  ],
}

let providerNodeSeed = 1

const route = useRoute()
const message = useMessage()

const loading = ref(true)
const saving = ref(false)
const syncingCourses = ref(false)

const account = ref<AccountItem | null>(null)
const config = ref<AccountStudyConfig | null>(null)
const courses = ref<CourseItem[]>([])
const providerMode = ref<ProviderMode>('single')
const providerNodes = ref<ProviderNode[]>([createProviderNode()])
const providerExtraJson = ref('{}')

const accountId = computed(() => Number(route.params.id))
const singleProviderNode = computed(() => providerNodes.value[0] ?? createProviderNode())

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isProviderKey(value: unknown): value is ProviderKey {
  return typeof value === 'string' && value in PROVIDER_FIELD_MAP
}

function isProviderConfigValue(value: unknown): value is ProviderConfigValue {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

function getProviderFields(provider: ProviderKey | null): ProviderFieldDef[] {
  return provider ? PROVIDER_FIELD_MAP[provider] : []
}

function buildDefaultProviderConfig(provider: ProviderKey): Record<string, ProviderConfigValue> {
  const defaults: Record<string, ProviderConfigValue> = {}
  for (const field of PROVIDER_FIELD_MAP[provider]) {
    if (field.defaultValue !== undefined) {
      defaults[field.key] = field.defaultValue
    }
  }
  return defaults
}

function pickKnownProviderConfig(
  provider: ProviderKey,
  rawConfig: Record<string, unknown>,
): Record<string, ProviderConfigValue> {
  const picked = buildDefaultProviderConfig(provider)
  for (const field of PROVIDER_FIELD_MAP[provider]) {
    const value = rawConfig[field.key]
    if (isProviderConfigValue(value)) {
      picked[field.key] = value
    }
  }
  return picked
}

function omitProviderFieldKeys(provider: ProviderKey, rawConfig: Record<string, unknown>): Record<string, unknown> {
  const fieldKeys = new Set(PROVIDER_FIELD_MAP[provider].map((field) => field.key))
  return Object.fromEntries(Object.entries(rawConfig).filter(([key]) => !fieldKeys.has(key)))
}

function createProviderNode(
  provider: ProviderKey | null = null,
  configValue: Record<string, ProviderConfigValue> = {},
): ProviderNode {
  return {
    id: providerNodeSeed++,
    provider,
    config: provider ? { ...buildDefaultProviderConfig(provider), ...configValue } : { ...configValue },
  }
}

function normalizeProviderStateForMode(mode: ProviderMode): void {
  if (mode === 'single') {
    const firstSelected = providerNodes.value.find((item) => item.provider) ?? providerNodes.value[0] ?? createProviderNode()
    providerNodes.value = [createProviderNode(firstSelected.provider, firstSelected.config)]
    return
  }

  if (providerNodes.value.length === 0) {
    providerNodes.value = [createProviderNode(), createProviderNode()]
    return
  }

  if (providerNodes.value.length === 1) {
    providerNodes.value = [...providerNodes.value, createProviderNode()]
  }
}

function handleProviderModeChange(value: ProviderMode): void {
  providerMode.value = value
  normalizeProviderStateForMode(value)
}

function updateProvider(node: ProviderNode, provider: ProviderKey | null): void {
  node.provider = provider
  node.config = provider ? buildDefaultProviderConfig(provider) : {}
}

function addProviderNode(): void {
  providerNodes.value.push(createProviderNode())
}

function removeProviderNode(index: number): void {
  if (providerNodes.value.length <= 1) {
    providerNodes.value = [createProviderNode()]
    return
  }
  providerNodes.value.splice(index, 1)
  if (providerMode.value === 'single') {
    normalizeProviderStateForMode('single')
  }
}

function moveProviderNode(index: number, offset: -1 | 1): void {
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= providerNodes.value.length) {
    return
  }
  const nextNodes = [...providerNodes.value]
  const current = nextNodes[index]
  if (!current) {
    return
  }
  nextNodes.splice(index, 1)
  nextNodes.splice(targetIndex, 0, current)
  providerNodes.value = nextNodes
}

function providerOptionsFor(nodeId: number): Array<{ label: string; value: ProviderKey; disabled?: boolean }> {
  const selectedProviders = new Set(
    providerNodes.value
      .filter((item) => item.id !== nodeId && item.provider !== null)
      .map((item) => item.provider as ProviderKey),
  )
  return PROVIDER_OPTIONS.map((option) => ({
    ...option,
    disabled: providerMode.value === 'chain' && selectedProviders.has(option.value),
  }))
}

function readProviderField(node: ProviderNode, field: ProviderFieldDef): ProviderConfigValue | null {
  const value = node.config[field.key]
  if (value !== undefined) {
    return value
  }
  if (field.defaultValue !== undefined) {
    return field.defaultValue
  }
  return field.type === 'switch' ? false : null
}

function setProviderField(node: ProviderNode, key: string, value: ProviderConfigValue | null): void {
  if (value === null || value === undefined || value === '') {
    delete node.config[key]
    return
  }
  node.config[key] = value
}

function safeParseConfigJson(jsonText?: string): Record<string, unknown> {
  if (!jsonText?.trim()) {
    return {}
  }

  try {
    const parsed = JSON.parse(jsonText)
    return isRecord(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

function parseProviderChain(rawValue: unknown): ProviderKey[] {
  if (Array.isArray(rawValue)) {
    return rawValue.filter(isProviderKey)
  }
  if (typeof rawValue === 'string') {
    const rawText = rawValue.trim()
    if (!rawText) {
      return []
    }
    if (rawText.startsWith('[')) {
      try {
        const parsed = JSON.parse(rawText)
        return Array.isArray(parsed) ? parsed.filter(isProviderKey) : []
      } catch {
        return []
      }
    }
    return rawText
      .split(/->|,/)
      .map((item) => item.trim())
      .filter(isProviderKey)
  }
  return []
}

function parseProviderEditorState(studyConfig: AccountStudyConfig): {
  mode: ProviderMode
  nodes: ProviderNode[]
  extraConfig: Record<string, unknown>
} {
  const rawConfig = safeParseConfigJson(studyConfig.providerConfigJson)
  const providerConfigsRaw = isRecord(rawConfig.provider_configs)
    ? (rawConfig.provider_configs as Record<string, unknown>)
    : {}
  const structuredChain = parseProviderChain(rawConfig.provider_chain)

  if (structuredChain.length > 0) {
    const nodes = structuredChain.map((provider) =>
      createProviderNode(
        provider,
        pickKnownProviderConfig(provider, isRecord(providerConfigsRaw[provider]) ? providerConfigsRaw[provider] : {}),
      ),
    )

    const extraConfig = Object.fromEntries(
      Object.entries(rawConfig).filter(([key]) => !['mode', 'provider_chain', 'provider_configs'].includes(key)),
    )

    const extraProviderConfigs: Record<string, unknown> = {}
    for (const [provider, value] of Object.entries(providerConfigsRaw)) {
      if (!isRecord(value)) {
        continue
      }
      if (!isProviderKey(provider)) {
        extraProviderConfigs[provider] = value
        continue
      }
      const unknownConfig = omitProviderFieldKeys(provider, value)
      if (Object.keys(unknownConfig).length > 0) {
        extraProviderConfigs[provider] = unknownConfig
      }
    }
    if (Object.keys(extraProviderConfigs).length > 0) {
      extraConfig.provider_configs = extraProviderConfigs
    }

    return {
      mode: rawConfig.mode === 'single' ? 'single' : structuredChain.length > 1 ? 'chain' : 'single',
      nodes,
      extraConfig,
    }
  }

  if (isProviderKey(studyConfig.answerProvider)) {
    const provider = studyConfig.answerProvider
    return {
      mode: 'single',
      nodes: [createProviderNode(provider, pickKnownProviderConfig(provider, rawConfig))],
      extraConfig: omitProviderFieldKeys(provider, rawConfig),
    }
  }

  return {
    mode: 'single',
    nodes: [createProviderNode()],
    extraConfig: rawConfig,
  }
}

function applyProviderEditorState(studyConfig: AccountStudyConfig): void {
  const state = parseProviderEditorState(studyConfig)
  providerMode.value = state.mode
  providerNodes.value = state.nodes.length > 0 ? state.nodes : [createProviderNode()]
  normalizeProviderStateForMode(state.mode)
  providerExtraJson.value = JSON.stringify(state.extraConfig, null, 2)
}

function hasProviderNodeContent(node: ProviderNode): boolean {
  return Object.keys(node.config).length > 0
}

function parseExtraProviderConfig(): Record<string, unknown> | null {
  const rawText = providerExtraJson.value.trim() || '{}'

  try {
    const parsed = JSON.parse(rawText)
    if (!isRecord(parsed)) {
      message.error('高级附加配置必须是 JSON 对象')
      return null
    }
    return parsed
  } catch {
    message.error('高级附加配置 JSON 格式不正确')
    return null
  }
}

function buildProviderPayload():
  | {
      answerProvider: string
      providerConfigJson: string
    }
  | null {
  const extraConfig = parseExtraProviderConfig()
  if (extraConfig === null) {
    return null
  }

  const candidateNodes = providerMode.value === 'single' ? providerNodes.value.slice(0, 1) : providerNodes.value
  const selectedNodes: Array<{ provider: ProviderKey; config: Record<string, ProviderConfigValue> }> = []

  for (const node of candidateNodes) {
    if (!node.provider) {
      if (hasProviderNodeContent(node)) {
        message.error('有一条 provider 配置还没选择 provider')
        return null
      }
      continue
    }

    selectedNodes.push({
      provider: node.provider,
      config: pickKnownProviderConfig(node.provider, node.config),
    })
  }

  const selectedProviderNames = selectedNodes.map((item) => item.provider)
  if (new Set(selectedProviderNames).size !== selectedProviderNames.length) {
    message.error('链式模式下不能重复选择同一个 provider')
    return null
  }

  const payloadExtraConfig = { ...extraConfig }
  const rawProviderConfigs = isRecord(payloadExtraConfig.provider_configs)
    ? (payloadExtraConfig.provider_configs as Record<string, unknown>)
    : {}
  delete payloadExtraConfig.mode
  delete payloadExtraConfig.provider_chain
  delete payloadExtraConfig.provider_configs

  const providerConfigsPayload: Record<string, Record<string, unknown>> = {}
  for (const [provider, value] of Object.entries(rawProviderConfigs)) {
    if (!isRecord(value)) {
      continue
    }
    if (!isProviderKey(provider) || !selectedProviderNames.includes(provider)) {
      providerConfigsPayload[provider] = { ...value }
    }
  }

  for (const node of selectedNodes) {
    const preservedExtra =
      isRecord(rawProviderConfigs[node.provider])
        ? omitProviderFieldKeys(node.provider, rawProviderConfigs[node.provider] as Record<string, unknown>)
        : {}
    providerConfigsPayload[node.provider] = {
      ...preservedExtra,
      ...node.config,
    }
  }

  const providerConfigPayload: Record<string, unknown> = { ...payloadExtraConfig }
  if (selectedNodes.length > 0) {
    providerConfigPayload.mode = providerMode.value
    providerConfigPayload.provider_chain = selectedProviderNames
    providerConfigPayload.provider_configs = providerConfigsPayload
  } else if (Object.keys(providerConfigsPayload).length > 0) {
    providerConfigPayload.provider_configs = providerConfigsPayload
  }

  return {
    answerProvider: selectedNodes[0]?.provider ?? '',
    providerConfigJson: Object.keys(providerConfigPayload).length > 0 ? JSON.stringify(providerConfigPayload) : '{}',
  }
}

function handleSingleProviderChange(value: string | null): void {
  updateProvider(singleProviderNode.value, isProviderKey(value) ? value : null)
}

function handleSingleProviderFieldChange(key: string, value: ProviderConfigValue | null): void {
  setProviderField(singleProviderNode.value, key, value)
}

function handleNodeProviderChange(node: ProviderNode, value: string | null): void {
  updateProvider(node, isProviderKey(value) ? value : null)
}

function handleNodeFieldChange(node: ProviderNode, key: string, value: ProviderConfigValue | null): void {
  setProviderField(node, key, value)
}

async function loadDetail(): Promise<void> {
  loading.value = true
  try {
    const detail = await getAccountDetail(accountId.value)
    account.value = detail.account
    config.value = {
      ...detail.config,
      providerConfigJson: detail.config.providerConfigJson ?? '{}',
    }
    applyProviderEditorState(config.value)
    courses.value = detail.courses
  } finally {
    loading.value = false
  }
}

async function saveAccount(): Promise<void> {
  if (!account.value || !config.value) {
    return
  }

  const providerPayload = buildProviderPayload()
  if (!providerPayload) {
    return
  }

  saving.value = true
  try {
    const payload: UpdateAccountPayload = {
      name: account.value.name.trim(),
      username: account.value.username.trim(),
      passwordEncrypted: account.value.passwordEncrypted?.trim() || '',
      cookiesPath: account.value.cookiesPath?.trim() || undefined,
      status: account.value.status,
      config: {
        ...config.value,
        answerProvider: providerPayload.answerProvider,
        speed: config.value.speed ?? 1,
        jobs: config.value.jobs ?? 4,
        confidenceThreshold: config.value.confidenceThreshold ?? 0.8,
        minCoverRate: config.value.minCoverRate ?? 0.7,
        providerConfigJson: providerPayload.providerConfigJson,
      },
    }
    const detail = await updateAccount(accountId.value, payload)
    account.value = detail.account
    config.value = {
      ...detail.config,
      providerConfigJson: detail.config.providerConfigJson ?? '{}',
    }
    applyProviderEditorState(config.value)
    courses.value = detail.courses
    message.success('账号配置已保存')
  } catch (error: unknown) {
    const maybeAxiosError = error as { response?: { status?: number } }
    if (maybeAxiosError?.response?.status === 409) {
      message.error('该账号已存在')
    } else {
      message.error('保存失败，请检查输入内容')
    }
  } finally {
    saving.value = false
  }
}

async function refreshCourses(): Promise<void> {
  syncingCourses.value = true
  try {
    const response = await syncAccountCourses(accountId.value)
    account.value = response.detail.account
    config.value = {
      ...response.detail.config,
      providerConfigJson: response.detail.config.providerConfigJson ?? '{}',
    }
    applyProviderEditorState(config.value)
    courses.value = response.detail.courses
    message.success(`课程同步完成，已获取 ${response.summary.courseCount} 门课程`)
  } catch (error) {
    message.error('课程同步失败，请检查 cookies 或账号密码')
  } finally {
    syncingCourses.value = false
  }
}

onMounted(async () => {
  await loadDetail()
})
</script>

<template>
  <n-space vertical size="large">
    <n-grid x-gap="16" y-gap="16" cols="1 l:2" responsive="screen">
      <n-grid-item>
        <n-card :bordered="false" :loading="loading" title="账号信息">
          <n-form v-if="account" label-placement="top">
            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="账号名称">
                  <n-input v-model:value="account.name" placeholder="例如：主账号" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="账号状态">
                  <n-select
                    v-model:value="account.status"
                    :options="[
                      { label: '启用', value: 'active' },
                      { label: '停用', value: 'disabled' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-form-item label="超星账号">
              <n-input v-model:value="account.username" placeholder="手机号 / 学号" />
            </n-form-item>
            <n-form-item label="密码">
              <n-input
                v-model:value="account.passwordEncrypted"
                type="password"
                show-password-on="click"
                placeholder="可留空，仅依赖 cookies 登录"
              />
            </n-form-item>
            <n-form-item label="Cookies 路径">
              <n-input v-model:value="account.cookiesPath" placeholder="留空则写入后端 accounts_dir/用户名.json" />
            </n-form-item>

            <n-space justify="space-between">
              <n-text depth="3">
                最近登录：{{ formatDateTime(account.lastLoginAt) }}
              </n-text>
              <n-space>
                <n-button :loading="syncingCourses" @click="refreshCourses">同步课程</n-button>
                <n-button type="primary" :loading="saving" @click="saveAccount">保存配置</n-button>
              </n-space>
            </n-space>
          </n-form>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card :bordered="false" :loading="loading" title="刷课策略">
          <n-form v-if="config" label-placement="top">
            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="视频倍速">
                  <n-input-number v-model:value="config.speed" :min="1" :max="2" :step="0.1" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="章节并发数">
                  <n-input-number v-model:value="config.jobs" :min="1" :max="8" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="未开放章节处理">
                  <n-select
                    v-model:value="config.notopenAction"
                    :options="[
                      { label: '重试', value: 'retry' },
                      { label: '跳过', value: 'continue' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="答题提交模式">
                  <n-select
                    v-model:value="config.submissionMode"
                    :options="[
                      { label: '智能提交', value: 'intelligent' },
                      { label: '自动提交', value: 'auto' },
                      { label: '仅保存不交卷', value: 'manual' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-grid x-gap="12" cols="1 s:2" responsive="screen">
              <n-grid-item>
                <n-form-item label="Provider 模式">
                  <n-radio-group :value="providerMode" @update:value="handleProviderModeChange">
                    <n-radio-button value="single">单 Provider</n-radio-button>
                    <n-radio-button value="chain">链式 Provider</n-radio-button>
                  </n-radio-group>
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="低置信度动作">
                  <n-select
                    v-model:value="config.lowConfidenceAction"
                    :options="[
                      { label: '暂停等待人工', value: 'pause' },
                      { label: '跳过', value: 'skip' },
                      { label: '仅保存', value: 'save_only' },
                    ]"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-alert type="info" :show-icon="false" style="margin-bottom: 16px">
              <template v-if="providerMode === 'single'">
                选择一个 provider 后，直接填写对应字段。留空时继续沿用 `backend.ini` 里的 `[tiku]` 默认配置。
              </template>
              <template v-else>
                链式模式会按顺序查询多个 provider。后面的 AI / SiliconFlow 会把前面渠道的答案作为参考，再自行判断最终答案。
              </template>
            </n-alert>

            <template v-if="providerMode === 'single'">
              <n-form-item label="答题 Provider">
                <n-select
                  :value="singleProviderNode.provider"
                  clearable
                  placeholder="留空则沿用 backend.ini 的 [tiku]"
                  :options="providerOptionsFor(singleProviderNode.id)"
                  @update:value="handleSingleProviderChange"
                />
              </n-form-item>

              <n-grid
                v-if="singleProviderNode.provider"
                x-gap="12"
                y-gap="12"
                cols="1 s:2"
                responsive="screen"
              >
                <n-grid-item
                  v-for="field in getProviderFields(singleProviderNode.provider)"
                  :key="field.key"
                >
                  <n-form-item :label="field.label">
                    <n-input
                      v-if="field.type === 'input'"
                      :value="String(readProviderField(singleProviderNode, field) ?? '')"
                      :placeholder="field.placeholder"
                      @update:value="(value) => handleSingleProviderFieldChange(field.key, value)"
                    />
                    <n-input
                      v-else-if="field.type === 'password'"
                      :value="String(readProviderField(singleProviderNode, field) ?? '')"
                      type="password"
                      show-password-on="click"
                      :placeholder="field.placeholder"
                      @update:value="(value) => handleSingleProviderFieldChange(field.key, value)"
                    />
                    <n-input-number
                      v-else-if="field.type === 'number'"
                      :value="typeof readProviderField(singleProviderNode, field) === 'number' ? Number(readProviderField(singleProviderNode, field)) : null"
                      :min="field.min"
                      :max="field.max"
                      :step="field.step"
                      style="width: 100%"
                      @update:value="(value) => handleSingleProviderFieldChange(field.key, value)"
                    />
                    <n-switch
                      v-else
                      :value="Boolean(readProviderField(singleProviderNode, field))"
                      @update:value="(value: boolean) => handleSingleProviderFieldChange(field.key, value)"
                    />
                  </n-form-item>
                </n-grid-item>
              </n-grid>
            </template>

            <template v-else>
              <n-space vertical size="large">
                <n-card
                  v-for="(node, index) in providerNodes"
                  :key="node.id"
                  size="small"
                  :title="`链路 ${index + 1}`"
                >
                  <template #header-extra>
                    <n-space size="small">
                      <n-button quaternary size="small" :disabled="index === 0" @click="moveProviderNode(index, -1)">
                        上移
                      </n-button>
                      <n-button
                        quaternary
                        size="small"
                        :disabled="index === providerNodes.length - 1"
                        @click="moveProviderNode(index, 1)"
                      >
                        下移
                      </n-button>
                      <n-button quaternary size="small" type="error" @click="removeProviderNode(index)">
                        删除
                      </n-button>
                    </n-space>
                  </template>

                  <n-form-item label="Provider">
                    <n-select
                      :value="node.provider"
                      clearable
                      placeholder="选择当前节点 provider"
                      :options="providerOptionsFor(node.id)"
                      @update:value="(value) => handleNodeProviderChange(node, value)"
                    />
                  </n-form-item>

                  <n-grid v-if="node.provider" x-gap="12" y-gap="12" cols="1 s:2" responsive="screen">
                    <n-grid-item v-for="field in getProviderFields(node.provider)" :key="field.key">
                      <n-form-item :label="field.label">
                        <n-input
                          v-if="field.type === 'input'"
                          :value="String(readProviderField(node, field) ?? '')"
                          :placeholder="field.placeholder"
                          @update:value="(value) => handleNodeFieldChange(node, field.key, value)"
                        />
                        <n-input
                          v-else-if="field.type === 'password'"
                          :value="String(readProviderField(node, field) ?? '')"
                          type="password"
                          show-password-on="click"
                          :placeholder="field.placeholder"
                          @update:value="(value) => handleNodeFieldChange(node, field.key, value)"
                        />
                        <n-input-number
                          v-else-if="field.type === 'number'"
                          :value="typeof readProviderField(node, field) === 'number' ? Number(readProviderField(node, field)) : null"
                          :min="field.min"
                          :max="field.max"
                          :step="field.step"
                          style="width: 100%"
                          @update:value="(value) => handleNodeFieldChange(node, field.key, value)"
                        />
                        <n-switch
                          v-else
                          :value="Boolean(readProviderField(node, field))"
                          @update:value="(value: boolean) => handleNodeFieldChange(node, field.key, value)"
                        />
                      </n-form-item>
                    </n-grid-item>
                  </n-grid>

                  <n-text v-else depth="3">
                    先选择 provider，再填写该节点对应的配置字段。
                  </n-text>
                </n-card>

                <n-button dashed block @click="addProviderNode">添加链路节点</n-button>
              </n-space>
            </template>

            <n-grid x-gap="12" cols="1 s:2" responsive="screen" style="margin-top: 16px">
              <n-grid-item>
                <n-form-item label="置信度阈值">
                  <n-input-number v-model:value="config.confidenceThreshold" :min="0" :max="1" :step="0.05" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="最低覆盖率">
                  <n-input-number v-model:value="config.minCoverRate" :min="0" :max="1" :step="0.05" style="width: 100%" />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-form-item label="高级附加配置(JSON，可选)">
              <n-input
                v-model:value="providerExtraJson"
                type="textarea"
                :autosize="{ minRows: 3, maxRows: 8 }"
                placeholder='{"check_llm_connection":"false"}'
              />
            </n-form-item>

            <n-checkbox v-model:checked="config.allowAiAutoSubmit">
              允许 AI 答案自动提交
            </n-checkbox>
          </n-form>
        </n-card>
      </n-grid-item>
    </n-grid>

    <n-card :bordered="false" :loading="loading" title="课程快照">
      <template #header-extra>
        <n-tag type="info">{{ courses.length }} 门课程</n-tag>
      </template>

      <n-data-table
        :columns="[
          { title: '课程名', key: 'title' },
          { title: '教师', key: 'teacher' },
          { title: '课程 ID', key: 'courseId' },
          { title: '班级 ID', key: 'clazzId' },
          { title: '同步时间', key: 'fetchedAt', render: (row: CourseItem) => formatDateTime(row.fetchedAt) },
        ]"
        :data="courses"
        :pagination="false"
      >
        <template #empty>
          请先点击“同步课程”拉取该账号的课程列表
        </template>
      </n-data-table>
    </n-card>
  </n-space>
</template>
