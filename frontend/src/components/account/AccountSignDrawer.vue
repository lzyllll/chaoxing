<script setup lang="ts">
import { useElementSize } from '@vueuse/core'
import { computed, h, ref, watch } from 'vue'
import { NButton, NDrawer, NDrawerContent, NSlider, NSpace, NTag, useMessage } from 'naive-ui'

import {
  getCourseSigns,
  getSignCaptcha,
  inspectSign,
  recognizeSignCaptcha,
  submitSign,
  submitSignWithCaptcha,
  uploadSignPhoto,
} from '@/api/client'
import LocationPickerMap from '@/components/account/LocationPickerMap.vue'
import type {
  CourseItem,
  CourseSignsResponse,
  SignActivityItem,
  SignCaptchaDataItem,
  SignContextPayload,
  SignInspectResponse,
  SignLocationPayload,
  SignPhotoUploadItem,
  SignSubmitPayload,
  SignSubmitResultItem,
  SignType,
} from '@/types'
import { formatDateTime } from '@/utils/format'

interface Props {
  show: boolean
  accountId: number
  course: CourseItem | null
}

interface SignFormState {
  signCode: string
  enc: string
  latitude: number | null
  longitude: number | null
  address: string
  objectId: string
  preSign: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const SIGN_TYPE_LABELS: Record<SignType, string> = {
  normal: '普通签到',
  photo: '拍照签到',
  qrcode: '二维码签到',
  location: '位置签到',
  gesture: '手势签到',
  signcode: '签到码签到',
  unknown: '未知类型',
}

const message = useMessage()

const loadingSigns = ref(false)
const inspecting = ref(false)
const submitting = ref(false)
const refreshingCaptcha = ref(false)
const recognizingCaptcha = ref(false)
const uploadingPhoto = ref(false)

const signPage = ref<CourseSignsResponse | null>(null)
const selectedActivity = ref<SignActivityItem | null>(null)
const inspection = ref<SignInspectResponse | null>(null)
const captchaData = ref<SignCaptchaDataItem | null>(null)
const submitResult = ref<SignSubmitResultItem | null>(null)
const photoUpload = ref<SignPhotoUploadItem | null>(null)
const resolvedSignedStates = ref<Record<string, boolean>>({})

const form = ref<SignFormState>(createEmptyForm())

const captchaStageRef = ref<HTMLElement | null>(null)
const { width: captchaStageWidth } = useElementSize(captchaStageRef)
const captchaSliderPx = ref(0)

const internalShow = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

const courseTitle = computed(() => signPage.value?.course.title ?? props.course?.title ?? '签到')
const resolvedSignType = computed<SignType>(
  () => inspection.value?.preflight.signType ?? inspection.value?.detail.signType ?? selectedActivity.value?.signType ?? 'unknown',
)
const requiresSignCode = computed(() => resolvedSignType.value === 'signcode' || resolvedSignType.value === 'gesture')
const requiresQrCode = computed(() => resolvedSignType.value === 'qrcode')
const requiresLocation = computed(() => resolvedSignType.value === 'location')
const allowsLocation = computed(() => requiresLocation.value || resolvedSignType.value === 'qrcode')
const requiresPhoto = computed(() => resolvedSignType.value === 'photo')
const targetLocationRange = computed(() => inspection.value?.detail.locationRange ?? null)
const targetLocationCenter = computed<SignLocationPayload | null>(() => {
  const detail = inspection.value?.detail
  if (detail?.locationLatitude == null || detail.locationLongitude == null) {
    return null
  }
  return {
    latitude: detail.locationLatitude,
    longitude: detail.locationLongitude,
    address: detail.locationText ?? '',
  }
})
const selectedLocationDistance = computed<number | null>(() => {
  if (!targetLocationCenter.value || form.value.latitude == null || form.value.longitude == null) {
    return null
  }
  return getDistanceMeters(
    form.value.latitude,
    form.value.longitude,
    targetLocationCenter.value.latitude,
    targetLocationCenter.value.longitude,
  )
})
const selectedLocationInRange = computed(() => {
  if (targetLocationRange.value == null || selectedLocationDistance.value == null) {
    return true
  }
  return selectedLocationDistance.value <= targetLocationRange.value
})
const pieceWidthPx = computed(() => Math.max(((captchaStageWidth.value || 320) * 56) / 320, 40))
const sliderMaxPx = computed(() => Math.max((captchaStageWidth.value || 320) - pieceWidthPx.value, 1))
const normalizedCaptchaX = computed(() => Number((((captchaSliderPx.value / sliderMaxPx.value) * 280) - 8).toFixed(2)))
const submitResultAlertType = computed<'success' | 'warning' | 'error' | 'info'>(() => {
  const status = submitResult.value?.status
  if (!status) {
    return 'info'
  }
  if (status === 'success' || status === 'already_signed') {
    return 'success'
  }
  if (status === 'captcha_required') {
    return 'warning'
  }
  if (status === 'ended' || status === 'wrong_location') {
    return 'warning'
  }
  return 'error'
})
const currentActivityTagType = computed<'default' | 'info' | 'success' | 'warning'>(() => {
  if (inspection.value?.preflight.alreadySigned || submitResult.value?.alreadySigned) {
    return 'success'
  }
  if (submitResult.value?.ended) {
    return 'warning'
  }
  if (selectedActivity.value) {
    return activityStatus(selectedActivity.value).type
  }
  return 'default'
})
const currentActivityStatusLabel = computed(() => {
  if (inspection.value?.preflight.alreadySigned || submitResult.value?.alreadySigned) {
    return '已签到'
  }
  if (submitResult.value?.ended) {
    return '已结束'
  }
  return selectedActivity.value ? activityStatus(selectedActivity.value).label : '未选择'
})

const activityColumns = computed(() => [
  { title: '签到名称', key: 'name' },
  {
    title: '类型',
    key: 'signType',
    render: (row: SignActivityItem) =>
      h(
        NTag,
        {
          size: 'small',
          bordered: false,
          type: signTypeTagType(row.signType),
        },
        { default: () => signTypeLabel(row.signType) },
      ),
  },
  {
    title: '开始时间',
    key: 'startTime',
    render: (row: SignActivityItem) => formatTimestamp(row.startTime),
  },
  {
    title: '结束时间',
    key: 'endTime',
    render: (row: SignActivityItem) => formatTimestamp(row.endTime),
  },
  {
    title: '状态',
    key: 'userStatus',
    render: (row: SignActivityItem) =>
      h(
        NTag,
        {
          size: 'small',
          bordered: false,
          type: activityStatus(row).type,
        },
        { default: () => activityStatus(row).label },
      ),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: SignActivityItem) =>
      h(
        NSpace,
        { size: 'small' },
        {
          default: () => [
            h(
              NButton,
              {
                size: 'small',
                type: isCurrentActivity(row) ? 'primary' : 'default',
                secondary: !isCurrentActivity(row),
                loading: inspecting.value && isCurrentActivity(row),
                onClick: () => void openActivity(row),
              },
              { default: () => (isCurrentActivity(row) ? '当前' : '处理') },
            ),
          ],
        },
      ),
  },
])

watch(
  sliderMaxPx,
  (value) => {
    if (captchaSliderPx.value > value) {
      captchaSliderPx.value = value
    }
  },
  { immediate: true },
)

watch(
  () => [props.show, props.course?.id] as const,
  async ([show, courseId]) => {
    if (show && courseId) {
      await loadSigns()
      return
    }
    if (!show) {
      resetAllState()
    }
  },
  { immediate: true },
)

function createEmptyForm(): SignFormState {
  return {
    signCode: '',
    enc: '',
    latitude: null,
    longitude: null,
    address: '',
    objectId: '',
    preSign: true,
  }
}

function signTypeLabel(signType: SignType | null | undefined): string {
  return SIGN_TYPE_LABELS[signType ?? 'unknown'] ?? SIGN_TYPE_LABELS.unknown
}

function signTypeTagType(signType: SignType): 'default' | 'info' | 'warning' | 'success' {
  if (signType === 'location' || signType === 'qrcode') {
    return 'warning'
  }
  if (signType === 'photo') {
    return 'info'
  }
  if (signType === 'signcode' || signType === 'gesture') {
    return 'success'
  }
  return 'default'
}

function formatTimestamp(value?: number | null): string {
  if (!value) {
    return '--'
  }
  const normalized = value < 1_000_000_000_000 ? value * 1000 : value
  return formatDateTime(new Date(normalized).toISOString())
}

function getDistanceMeters(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const earthRadius = 6371000
  const toRadians = (value: number) => (value * Math.PI) / 180
  const deltaLat = toRadians(lat2 - lat1)
  const deltaLng = toRadians(lng2 - lng1)
  const radLat1 = toRadians(lat1)
  const radLat2 = toRadians(lat2)
  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(radLat1) * Math.cos(radLat2) * Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2)
  return earthRadius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function activityStatus(activity: SignActivityItem): { label: string; type: 'default' | 'info' | 'success' | 'warning' } {
  if (resolvedSignedStates.value[getActivityKey(activity)] === true) {
    return { label: '已签到', type: 'success' }
  }
  if ((activity.endName || '').trim()) {
    return { label: activity.endName, type: 'warning' }
  }
  if (activity.status === 1) {
    return { label: '进行中', type: 'info' }
  }
  return { label: `待处理${activity.userStatus != null ? ` (${activity.userStatus})` : ''}`, type: 'default' }
}

function isCurrentActivity(activity: SignActivityItem): boolean {
  return selectedActivity.value?.activeId === activity.activeId && selectedActivity.value?.ext === activity.ext
}

function getActivityKey(activity: Pick<SignActivityItem, 'activeId' | 'ext'>): string {
  return `${activity.activeId}:${activity.ext}`
}

function buildContext(activity: SignActivityItem): SignContextPayload {
  return {
    activeId: activity.activeId,
    courseId: activity.courseId,
    classId: activity.classId,
    ext: activity.ext,
    signType: activity.signType,
  }
}

function applyInspectionDefaults(payload: SignInspectResponse): void {
  const detail = payload.preflight.detail ?? payload.detail
  const defaultAddress =
    payload.preflight.signType === 'location' || payload.detail.signType === 'location' ? detail.locationText ?? '' : ''
  form.value = {
    signCode: '',
    enc: '',
    latitude: detail.locationLatitude ?? null,
    longitude: detail.locationLongitude ?? null,
    address: defaultAddress,
    objectId: '',
    preSign: true,
  }
  photoUpload.value = null
}

function resetCaptchaState(): void {
  captchaSliderPx.value = 0
  captchaData.value = null
}

function resetSelectionState(): void {
  selectedActivity.value = null
  inspection.value = null
  submitResult.value = null
  photoUpload.value = null
  form.value = createEmptyForm()
  resetCaptchaState()
}

function resetAllState(): void {
  signPage.value = null
  resolvedSignedStates.value = {}
  resetSelectionState()
}

async function loadSigns(): Promise<void> {
  if (!props.course) {
    return
  }

  loadingSigns.value = true
  const selectedKey = selectedActivity.value ? getActivityKey(selectedActivity.value) : null
  try {
    const payload = await getCourseSigns(props.accountId, props.course.id)
    signPage.value = payload

    if (payload.activities.length === 0) {
      resetSelectionState()
      return
    }

    const nextActivity =
      payload.activities.find((item) => getActivityKey(item) === selectedKey) ?? payload.activities[0] ?? null

    if (nextActivity) {
      await openActivity(nextActivity)
    }
  } catch (error) {
    message.error(extractErrorMessage(error, '加载签到列表失败'))
  } finally {
    loadingSigns.value = false
  }
}

async function openActivity(activity: SignActivityItem): Promise<void> {
  selectedActivity.value = activity
  inspection.value = null
  submitResult.value = null
  resetCaptchaState()
  photoUpload.value = null
  inspecting.value = true

  try {
    const payload = await inspectSign(props.accountId, buildContext(activity))
    inspection.value = payload
    resolvedSignedStates.value = {
      ...resolvedSignedStates.value,
      [getActivityKey(activity)]: payload.preflight.alreadySigned,
    }
    applyInspectionDefaults(payload)
  } catch (error) {
    message.error(extractErrorMessage(error, '加载签到详情失败'))
  } finally {
    inspecting.value = false
  }
}

function maybeBuildLocation(required: boolean): SignLocationPayload | null {
  const address = form.value.address.trim()
  const latitude = form.value.latitude
  const longitude = form.value.longitude
  const hasAnyValue = address.length > 0 || latitude !== null || longitude !== null

  if (!hasAnyValue) {
    if (required) {
      throw new Error('请填写位置签到所需的经纬度和地址')
    }
    return null
  }

  if (latitude === null || longitude === null || !address) {
    throw new Error('位置参数未填写完整')
  }

  return {
    latitude,
    longitude,
    address,
  }
}

function ensureLocationWithinRange(location: SignLocationPayload | null): void {
  if (!location || targetLocationCenter.value == null || targetLocationRange.value == null) {
    return
  }
  const distance = getDistanceMeters(
    location.latitude,
    location.longitude,
    targetLocationCenter.value.latitude,
    targetLocationCenter.value.longitude,
  )
  if (distance > targetLocationRange.value) {
    throw new Error(`已选位置超出签到范围，当前距离中心约 ${Math.round(distance)} 米`)
  }
}

function buildSubmitPayload(): SignSubmitPayload {
  if (!selectedActivity.value) {
    throw new Error('请先选择签到活动')
  }

  if (inspection.value?.preflight.alreadySigned) {
    throw new Error('该签到已经完成')
  }

  if (requiresSignCode.value && !form.value.signCode.trim()) {
    throw new Error('请填写签到码或手势码')
  }

  if (requiresQrCode.value && !form.value.enc.trim()) {
    throw new Error('请填写二维码 enc 参数')
  }

  if (requiresPhoto.value && !form.value.objectId.trim()) {
    throw new Error('请先上传签到图片')
  }

  const location = allowsLocation.value ? maybeBuildLocation(requiresLocation.value) : null
  ensureLocationWithinRange(location)

  return {
    ...buildContext(selectedActivity.value),
    signType: resolvedSignType.value,
    signCode: form.value.signCode.trim() || null,
    enc: form.value.enc.trim() || null,
    location,
    objectId: form.value.objectId.trim() || null,
    preSign: form.value.preSign,
  }
}

function applyRecognizedCaptchaXPosition(xPosition: number): void {
  const sliderRatio = Math.max(0, Math.min(1, (xPosition + 8) / 280))
  captchaSliderPx.value = Number((sliderRatio * sliderMaxPx.value).toFixed(0))
}

function applySubmitResponse(payload: { result: SignSubmitResultItem; captchaData?: SignCaptchaDataItem }): void {
  submitResult.value = payload.result
  if (selectedActivity.value) {
    const currentKey = getActivityKey(selectedActivity.value)
    if (payload.result.alreadySigned || payload.result.status === 'success') {
      resolvedSignedStates.value = {
        ...resolvedSignedStates.value,
        [currentKey]: true,
      }
    }
  }
  if (payload.captchaData) {
    captchaData.value = payload.captchaData
    captchaSliderPx.value = 0
  } else if (!payload.result.captchaRequired) {
    resetCaptchaState()
  }

  if (payload.result.status === 'success') {
    message.success(payload.result.message || '签到成功')
    return
  }
  if (payload.result.status === 'already_signed') {
    message.success(payload.result.message || '该签到已完成')
    return
  }
  if (payload.result.status === 'captcha_required') {
    message.warning(payload.result.message || '需要验证码，请先手动拖动滑块')
    return
  }
  message.warning(payload.result.message || '签到未成功')
}

async function handleSubmit(): Promise<void> {
  try {
    submitting.value = true
    const payload = buildSubmitPayload()
    const response = await submitSign(props.accountId, payload)
    applySubmitResponse(response)
    if (response.result.status !== 'captcha_required') {
      await loadSigns()
    }
  } catch (error) {
    message.error(extractErrorMessage(error, '提交签到失败'))
  } finally {
    submitting.value = false
  }
}

async function refreshCaptcha(): Promise<void> {
  if (!selectedActivity.value) {
    return
  }

  refreshingCaptcha.value = true
  try {
    const response = await getSignCaptcha(props.accountId, buildContext(selectedActivity.value))
    captchaData.value = response.captchaData
    captchaSliderPx.value = 0
    message.success('验证码已刷新')
  } catch (error) {
    message.error(extractErrorMessage(error, '获取验证码失败'))
  } finally {
    refreshingCaptcha.value = false
  }
}

async function handleRecognizeCaptcha(): Promise<void> {
  if (!captchaData.value) {
    message.warning('请先获取验证码')
    return
  }

  recognizingCaptcha.value = true
  try {
    const response = await recognizeSignCaptcha(props.accountId, captchaData.value)
    applyRecognizedCaptchaXPosition(response.xPosition)
    message.success(`已识别建议位移，提交用 xPosition：${response.xPosition}`)
  } catch (error) {
    message.error(extractErrorMessage(error, '自动识别验证码失败'))
  } finally {
    recognizingCaptcha.value = false
  }
}

async function handleSubmitWithCaptcha(): Promise<void> {
  if (!captchaData.value) {
    message.warning('请先获取验证码')
    return
  }

  try {
    submitting.value = true
    const response = await submitSignWithCaptcha(props.accountId, {
      ...buildSubmitPayload(),
      xPosition: normalizedCaptchaX.value,
      captchaData: captchaData.value,
    })
    applySubmitResponse(response)
    if (response.result.status !== 'captcha_required') {
      await loadSigns()
    }
  } catch (error) {
    message.error(extractErrorMessage(error, '验证码签到失败'))
  } finally {
    submitting.value = false
  }
}

async function handlePhotoSelected(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0]
  if (!file) {
    return
  }

  uploadingPhoto.value = true
  try {
    const response = await uploadSignPhoto(props.accountId, file)
    photoUpload.value = response
    form.value.objectId = response.objectId
    message.success('签到图片已上传')
  } catch (error) {
    message.error(extractErrorMessage(error, '上传签到图片失败'))
  } finally {
    uploadingPhoto.value = false
    if (target) {
      target.value = ''
    }
  }
}

function extractErrorMessage(error: unknown, fallback: string): string {
  const maybeAxiosError = error as {
    response?: {
      data?: {
        detail?: string | Array<{ msg?: string }>
      }
    }
    message?: string
  }
  const detail = maybeAxiosError?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (first?.msg) {
      return first.msg
    }
  }
  if (maybeAxiosError?.message) {
    return maybeAxiosError.message
  }
  return fallback
}
</script>

<template>
  <n-drawer v-model:show="internalShow" :width="920" placement="right">
    <n-drawer-content closable :title="`签到管理 · ${courseTitle}`">
      <n-space vertical size="large">
        <n-card v-if="props.course" :bordered="false" embedded size="small">
          <n-space justify="space-between" wrap>
            <n-text>{{ props.course.title }}</n-text>
            <n-space size="small" align="center">
              <n-text depth="3">课程 ID {{ props.course.courseId }} / 班级 ID {{ props.course.clazzId }}</n-text>
              <n-button :disabled="!props.course" :loading="loadingSigns" quaternary @click="loadSigns">
                刷新签到
              </n-button>
            </n-space>
          </n-space>
        </n-card>

        <n-card :bordered="false" :loading="loadingSigns" title="签到列表">
          <n-data-table
            :columns="activityColumns"
            :data="signPage?.activities ?? []"
            :pagination="false"
            :single-line="false"
          >
            <template #empty>
              当前课程暂无可处理的签到活动
            </template>
          </n-data-table>
        </n-card>

        <n-card
          v-if="selectedActivity"
          :bordered="false"
          :loading="inspecting"
          title="签到处理"
        >
          <template #header-extra>
            <n-space size="small" align="center">
              <n-tag :bordered="false" :type="signTypeTagType(resolvedSignType)">
                {{ signTypeLabel(resolvedSignType) }}
              </n-tag>
              <n-tag :bordered="false" :type="currentActivityTagType">
                {{ currentActivityStatusLabel }}
              </n-tag>
            </n-space>
          </template>

          <n-space vertical size="large">
            <n-descriptions v-if="inspection" label-placement="left" :column="2">
              <n-descriptions-item label="活动 ID">
                {{ inspection.context.activeId }}
              </n-descriptions-item>
              <n-descriptions-item label="预检结果">
                {{ inspection.preflight.analysisCode || '未返回' }}
              </n-descriptions-item>
              <n-descriptions-item label="开始时间">
                {{ formatTimestamp(inspection.detail.startTime) }}
              </n-descriptions-item>
              <n-descriptions-item label="结束时间">
                {{ formatTimestamp(inspection.detail.endTime) }}
              </n-descriptions-item>
              <n-descriptions-item v-if="inspection.detail.locationText" label="目标地址">
                {{ inspection.detail.locationText }}
              </n-descriptions-item>
              <n-descriptions-item v-if="inspection.detail.locationRange != null" label="签到范围">
                {{ inspection.detail.locationRange }} 米
              </n-descriptions-item>
            </n-descriptions>

            <n-alert
              v-if="inspection?.preflight.alreadySigned"
              type="success"
              title="该签到已经完成"
            >
              当前账号已在超星侧完成签到，下面的表单仅作查看。
            </n-alert>

            <n-alert
              v-if="submitResult"
              :type="submitResultAlertType"
              :title="submitResult.message || '签到结果'"
            >
              <template v-if="submitResult.status === 'captcha_required'">
                需要手动拖动滑块，或者点击“自动识别”获取建议位移后再提交验证码。
              </template>
              <template v-else-if="submitResult.rawResponse">
                原始响应：{{ submitResult.rawResponse }}
              </template>
            </n-alert>

            <n-form label-placement="top">
              <n-grid x-gap="12" y-gap="12" cols="1 s:2" responsive="screen">
                <n-grid-item v-if="requiresSignCode">
                  <n-form-item :label="resolvedSignType === 'gesture' ? '手势码' : '签到码'">
                    <n-input
                      v-model:value="form.signCode"
                      :placeholder="resolvedSignType === 'gesture' ? '输入手势码' : '输入签到码'"
                    />
                  </n-form-item>
                </n-grid-item>

                <n-grid-item v-if="requiresQrCode">
                  <n-form-item label="二维码 enc">
                    <n-input v-model:value="form.enc" placeholder="扫码后得到的 enc 参数" />
                  </n-form-item>
                </n-grid-item>

                <n-grid-item v-if="allowsLocation">
                  <n-form-item label="纬度">
                    <n-input-number v-model:value="form.latitude" :step="0.000001" style="width: 100%" />
                  </n-form-item>
                </n-grid-item>

                <n-grid-item v-if="allowsLocation">
                  <n-form-item label="经度">
                    <n-input-number v-model:value="form.longitude" :step="0.000001" style="width: 100%" />
                  </n-form-item>
                </n-grid-item>
              </n-grid>

              <n-form-item v-if="allowsLocation" label="位置地址">
                <n-input v-model:value="form.address" placeholder="例如：教学楼 A-101" />
              </n-form-item>

              <n-form-item v-if="allowsLocation" label="地图选点">
                <LocationPickerMap
                  v-model:latitude="form.latitude"
                  v-model:longitude="form.longitude"
                  v-model:address="form.address"
                  :disabled="Boolean(inspection?.preflight.alreadySigned)"
                  :target-address="inspection?.detail.locationText ?? null"
                  :target-latitude="inspection?.detail.locationLatitude ?? null"
                  :target-longitude="inspection?.detail.locationLongitude ?? null"
                  :target-range="inspection?.detail.locationRange ?? null"
                />
              </n-form-item>

              <n-alert
                v-if="allowsLocation && targetLocationRange != null && selectedLocationDistance != null && !selectedLocationInRange"
                type="warning"
                :show-icon="false"
              >
                已选位置超出签到范围，当前距离中心约 {{ Math.round(selectedLocationDistance) }} 米。
              </n-alert>

              <template v-if="requiresPhoto">
                <n-form-item label="签到图片">
                  <n-space vertical size="small" style="width: 100%">
                    <input accept="image/*" type="file" @change="handlePhotoSelected" />
                    <n-text depth="3">
                      {{ form.objectId ? `已上传 objectId: ${form.objectId}` : '请选择一张图片上传到超星后再提交签到。' }}
                    </n-text>
                    <n-text v-if="photoUpload?.filePath" depth="3">
                      文件路径：{{ photoUpload.filePath }}
                    </n-text>
                  </n-space>
                </n-form-item>
              </template>

              <n-form-item label="预检签到页">
                <n-switch v-model:value="form.preSign" />
              </n-form-item>
            </n-form>

            <n-space wrap>
              <n-button
                type="primary"
                :disabled="inspection?.preflight.alreadySigned"
                :loading="submitting"
                @click="handleSubmit"
              >
                先尝试签到
              </n-button>
              <n-button
                v-if="captchaData"
                secondary
                :disabled="inspection?.preflight.alreadySigned"
                :loading="submitting"
                @click="handleSubmitWithCaptcha"
              >
                提交验证码并签到
              </n-button>
              <n-button
                :disabled="inspection?.preflight.alreadySigned"
                :loading="refreshingCaptcha"
                @click="refreshCaptcha"
              >
                获取验证码
              </n-button>
              <n-button
                v-if="captchaData"
                tertiary
                :disabled="inspection?.preflight.alreadySigned"
                :loading="recognizingCaptcha"
                @click="handleRecognizeCaptcha"
              >
                自动识别
              </n-button>
              <n-button v-if="uploadingPhoto" :loading="uploadingPhoto" disabled>
                上传中
              </n-button>
            </n-space>

            <n-card v-if="captchaData" embedded size="small" title="手动滑块验证码">
              <n-space vertical size="large">
                <n-alert type="info" :show-icon="false">
                  拖动滑块让拼图与缺口对齐。自动识别只会回填建议位置，提交前请自行确认。当前换算后的 x 位移为 {{ normalizedCaptchaX }}。
                </n-alert>

                <div ref="captchaStageRef" class="sign-captcha-stage">
                  <img :src="captchaData.shadeImage" alt="captcha background" class="sign-captcha-stage__background" />
                  <img
                    :src="captchaData.cutoutImage"
                    alt="captcha cutout"
                    class="sign-captcha-stage__piece"
                    :style="{
                      width: `${pieceWidthPx}px`,
                      transform: `translateX(${captchaSliderPx}px)`,
                    }"
                  />
                </div>

                <n-grid x-gap="12" cols="1 s:2" responsive="screen">
                  <n-grid-item>
                    <n-form-item label="滑块位置">
                      <n-slider v-model:value="captchaSliderPx" :max="sliderMaxPx" :step="1" />
                    </n-form-item>
                  </n-grid-item>
                  <n-grid-item>
                    <n-space vertical size="small" class="sign-captcha-metrics">
                      <n-text>当前像素位移：{{ Math.round(captchaSliderPx) }} px</n-text>
                      <n-text>提交用 xPosition：{{ normalizedCaptchaX }}</n-text>
                    </n-space>
                  </n-grid-item>
                </n-grid>
              </n-space>
            </n-card>
          </n-space>
        </n-card>
      </n-space>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.sign-captcha-stage {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  background: #f4f4f5;
}

.sign-captcha-stage__background {
  display: block;
  width: 100%;
  height: auto;
}

.sign-captcha-stage__piece {
  position: absolute;
  top: 0;
  left: 0;
  height: auto;
  max-width: none;
  pointer-events: none;
  filter: drop-shadow(0 8px 18px rgba(15, 23, 42, 0.28));
}

.sign-captcha-metrics {
  min-height: 100%;
  justify-content: center;
}
</style>
