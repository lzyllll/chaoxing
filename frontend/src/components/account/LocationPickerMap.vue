<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useMessage } from 'naive-ui'

import { frontendRuntime } from '@/config/runtime'

interface Props {
  latitude: number | null
  longitude: number | null
  address?: string
  targetLatitude?: number | null
  targetLongitude?: number | null
  targetRange?: number | null
  targetAddress?: string | null
  disabled?: boolean
}

declare global {
  interface Window {
    BMap?: any
    __chaoxingBaiduReady__?: () => void
    __chaoxingBaiduLoader__?: Promise<any>
  }
}

const props = withDefaults(defineProps<Props>(), {
  address: '',
  targetLatitude: null,
  targetLongitude: null,
  targetRange: null,
  targetAddress: null,
  disabled: false,
})

const emit = defineEmits<{
  'update:latitude': [value: number | null]
  'update:longitude': [value: number | null]
  'update:address': [value: string]
}>()

function loadBaiduMapSdk(): Promise<any> {
  if (window.BMap) {
    return Promise.resolve(window.BMap)
  }
  if (!frontendRuntime.baiduMapAk) {
    return Promise.reject(new Error('未配置 VITE_BAIDU_MAP_AK，无法启用地图选点'))
  }
  if (window.__chaoxingBaiduLoader__) {
    return window.__chaoxingBaiduLoader__
  }

  window.__chaoxingBaiduLoader__ = new Promise((resolve, reject) => {
    const callbackName = '__chaoxingBaiduReady__'
    const existingScript = document.getElementById('chaoxing-baidu-map-sdk') as HTMLScriptElement | null

    window[callbackName] = () => {
      if (window.BMap) {
        resolve(window.BMap)
        return
      }
      window.__chaoxingBaiduLoader__ = undefined
      reject(new Error('百度地图脚本已加载，但 BMap 对象不可用'))
    }

    if (existingScript) {
      return
    }

    const script = document.createElement('script')
    script.id = 'chaoxing-baidu-map-sdk'
    script.async = true
    script.src =
      `https://api.map.baidu.com/api?v=3.0&ak=${encodeURIComponent(frontendRuntime.baiduMapAk)}` +
      `&callback=${callbackName}`
    script.onerror = () => {
      window.__chaoxingBaiduLoader__ = undefined
      reject(new Error('百度地图脚本加载失败，请检查网络或 AK 配置'))
    }
    document.head.appendChild(script)
  })

  return window.__chaoxingBaiduLoader__
}

const DEFAULT_CENTER: [number, number] = [116.404, 39.915]

const message = useMessage()
const mapContainerRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const loadError = ref('')
const baiduReady = ref(false)
const reverseGeocodeSeq = ref(0)
const targetSearchSeq = ref(0)
const targetSearchStatus = ref<'idle' | 'searching' | 'resolved' | 'failed'>('idle')
const searchedTargetCenter = ref<[number, number] | null>(null)
const lastSelectionSignature = ref('')

const mapInstance = shallowRef<any>(null)
const geocoder = shallowRef<any>(null)
const geolocation = shallowRef<any>(null)
const selectedMarker = shallowRef<any>(null)
const targetMarker = shallowRef<any>(null)
const targetCircle = shallowRef<any>(null)

const hasSdkKey = computed(() => Boolean(frontendRuntime.baiduMapAk))
const targetKeyword = computed(() => props.targetAddress?.trim() || '')
const targetCenter = computed<[number, number] | null>(() => searchedTargetCenter.value)
const selectedCenter = computed<[number, number] | null>(() => {
  if (props.longitude == null || props.latitude == null) {
    return null
  }
  return [props.longitude, props.latitude]
})
const distanceToTarget = computed<number | null>(() => {
  if (!targetCenter.value || !selectedCenter.value) {
    return null
  }
  return getDistanceMeters(
    selectedCenter.value[1],
    selectedCenter.value[0],
    targetCenter.value[1],
    targetCenter.value[0],
  )
})
const isWithinTargetRange = computed(() => {
  if (props.targetRange == null || distanceToTarget.value == null) {
    return true
  }
  return distanceToTarget.value <= props.targetRange
})
const rangeAlertType = computed<'info' | 'success' | 'warning'>(() => {
  if (props.targetRange == null || distanceToTarget.value == null) {
    return 'info'
  }
  return isWithinTargetRange.value ? 'success' : 'warning'
})
const rangeSummary = computed(() => {
  if (!targetKeyword.value) {
    return '地图点击后会自动回填经纬度和地址。'
  }
  if (targetSearchStatus.value === 'searching') {
    return `正在根据目标位置“${targetKeyword.value}”定位。`
  }
  if (!targetCenter.value) {
    return `未能根据目标位置“${targetKeyword.value}”定位，请手动选点。`
  }
  if (props.targetRange == null) {
    return `已根据目标位置“${targetKeyword.value}”完成定位。`
  }
  if (distanceToTarget.value == null) {
    return `当前签到范围 ${props.targetRange} 米，先在地图上选择位置。`
  }
  const distance = Math.round(distanceToTarget.value)
  return isWithinTargetRange.value
    ? `已选位置距签到中心 ${distance} 米，位于允许范围内。`
    : `已选位置距签到中心 ${distance} 米，超出允许范围 ${props.targetRange} 米。`
})

function roundCoordinate(value: number): number {
  return Number(value.toFixed(6))
}

function getDistanceMeters(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const earthRadius = 6371000
  const toRadians = (value: number) => (value * Math.PI) / 180
  const dLat = toRadians(lat2 - lat1)
  const dLng = toRadians(lng2 - lng1)
  const startLat = toRadians(lat1)
  const endLat = toRadians(lat2)
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(startLat) * Math.cos(endLat) * Math.sin(dLng / 2) * Math.sin(dLng / 2)
  return earthRadius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function normalizePoint(input: any): { lng: number; lat: number } | null {
  if (!input) {
    return null
  }
  if (typeof input.lng === 'number' && typeof input.lat === 'number') {
    return {
      lng: Number(input.lng),
      lat: Number(input.lat),
    }
  }
  return null
}

function toBaiduPoint(lng: number, lat: number): any {
  const BMap = window.BMap
  return BMap ? new BMap.Point(lng, lat) : null
}

function buildSelectionSignature(lng: number, lat: number): string {
  return `${lng.toFixed(6)}:${lat.toFixed(6)}`
}

function shouldSkipSelection(lng: number, lat: number): boolean {
  const signature = buildSelectionSignature(lng, lat)
  if (lastSelectionSignature.value === signature) {
    return true
  }
  lastSelectionSignature.value = signature
  return false
}

function resolvedMapCenter(): [number, number] {
  return selectedCenter.value ?? targetCenter.value ?? DEFAULT_CENTER
}

function emitCoordinates(lng: number, lat: number): void {
  emit('update:longitude', roundCoordinate(lng))
  emit('update:latitude', roundCoordinate(lat))
}

function centerMap(lng: number, lat: number, zoom = 18): void {
  const point = toBaiduPoint(lng, lat)
  if (!mapInstance.value || !point) {
    return
  }
  mapInstance.value.centerAndZoom(point, zoom)
}

function removeTargetOverlays(): void {
  if (mapInstance.value && targetMarker.value) {
    targetMarker.value.removeEventListener?.('click')
    mapInstance.value.removeOverlay(targetMarker.value)
  }
  if (mapInstance.value && targetCircle.value) {
    targetCircle.value.removeEventListener?.('click')
    mapInstance.value.removeOverlay(targetCircle.value)
  }
  targetMarker.value = null
  targetCircle.value = null
}

function syncSelectedMarker(): void {
  if (!baiduReady.value || !mapInstance.value) {
    return
  }

  if (!selectedCenter.value) {
    if (selectedMarker.value) {
      selectedMarker.value.removeEventListener?.('dragend')
      mapInstance.value.removeOverlay(selectedMarker.value)
      selectedMarker.value = null
    }
    return
  }

  const point = toBaiduPoint(selectedCenter.value[0], selectedCenter.value[1])
  if (!point) {
    return
  }

  if (!selectedMarker.value) {
    const BMap = window.BMap
    selectedMarker.value = new BMap.Marker(point)
    selectedMarker.value.addEventListener('dragend', (event: any) => {
      if (props.disabled) {
        return
      }
      const droppedPoint = normalizePoint(event?.point)
      if (!droppedPoint) {
        return
      }
      applySelection(droppedPoint.lng, droppedPoint.lat, {
        reverseGeocode: true,
        centerMap: false,
      })
    })
    mapInstance.value.addOverlay(selectedMarker.value)
  } else {
    selectedMarker.value.setPosition(point)
  }

  if (props.disabled) {
    selectedMarker.value.disableDragging?.()
  } else {
    selectedMarker.value.enableDragging?.()
  }
}

function syncTargetOverlay(): void {
  if (!baiduReady.value || !mapInstance.value) {
    return
  }

  removeTargetOverlays()
  if (!targetCenter.value) {
    return
  }

  const BMap = window.BMap
  const point = toBaiduPoint(targetCenter.value[0], targetCenter.value[1])
  if (!BMap || !point) {
    return
  }

  targetMarker.value = new BMap.Marker(point)
  targetMarker.value.addEventListener('click', () => {
    if (props.disabled) {
      return
    }
    applySelection(targetCenter.value![0], targetCenter.value![1], {
      reverseGeocode: false,
      centerMap: false,
    })
    if (targetKeyword.value) {
      emit('update:address', targetKeyword.value)
    }
  })
  mapInstance.value.addOverlay(targetMarker.value)

  if (props.targetRange != null) {
    targetCircle.value = new BMap.Circle(point, props.targetRange, {
      strokeColor: '#d03050',
      strokeWeight: 2,
      strokeOpacity: 0.7,
      fillColor: '#d03050',
      fillOpacity: 0.12,
    })
    targetCircle.value.addEventListener('click', (event: any) => {
      if (props.disabled) {
        return
      }
      const clickedPoint = normalizePoint(event?.point) ?? normalizePoint(point)
      if (!clickedPoint) {
        return
      }
      applySelection(clickedPoint.lng, clickedPoint.lat, {
        reverseGeocode: true,
        centerMap: false,
      })
    })
    mapInstance.value.addOverlay(targetCircle.value)
  }
}

function resolveAddressFromResult(result: any): string {
  const address = result?.address?.trim()
  const poiTitle = result?.surroundingPois?.[0]?.title?.trim()
  if (address && poiTitle && !address.includes(poiTitle)) {
    return `${address} ${poiTitle}`
  }
  return address || poiTitle || props.address || ''
}

function reverseGeocode(lng: number, lat: number): void {
  if (!geocoder.value) {
    return
  }
  const point = toBaiduPoint(lng, lat)
  if (!point) {
    return
  }

  const currentSeq = reverseGeocodeSeq.value + 1
  reverseGeocodeSeq.value = currentSeq
  geocoder.value.getLocation(point, (result: any) => {
    if (reverseGeocodeSeq.value !== currentSeq) {
      return
    }
    const nextAddress = resolveAddressFromResult(result)
    if (!nextAddress) {
      message.warning('地图点位已更新，但地址解析失败，请手动补充地址')
      return
    }
    emit('update:address', nextAddress)
  })
}

function applySelection(
  lng: number,
  lat: number,
  options: { reverseGeocode: boolean; centerMap: boolean },
): void {
  if (shouldSkipSelection(lng, lat)) {
    return
  }
  emitCoordinates(lng, lat)

  const point = toBaiduPoint(lng, lat)
  if (selectedMarker.value && point) {
    selectedMarker.value.setPosition(point)
  } else {
    syncSelectedMarker()
  }

  if (options.centerMap) {
    centerMap(lng, lat)
  }
  if (options.reverseGeocode) {
    reverseGeocode(lng, lat)
  }
}

function applyTargetSearchResult(center: [number, number] | null, shouldAutofillSelection: boolean): void {
  searchedTargetCenter.value = center
  targetSearchStatus.value = center ? 'resolved' : 'failed'
  syncTargetOverlay()

  if (!center) {
    return
  }

  if (!selectedCenter.value) {
    centerMap(center[0], center[1], 17)
  }
  if (shouldAutofillSelection && !selectedCenter.value && targetKeyword.value) {
    applySelection(center[0], center[1], {
      reverseGeocode: false,
      centerMap: true,
    })
    emit('update:address', targetKeyword.value)
  }
}

function fallbackGeocodeTarget(keyword: string, seq: number, shouldAutofillSelection: boolean): void {
  if (!geocoder.value) {
    applyTargetSearchResult(null, shouldAutofillSelection)
    return
  }

  geocoder.value.getPoint(keyword, (point: any) => {
    if (targetSearchSeq.value !== seq) {
      return
    }
    const resolvedPoint = normalizePoint(point)
    applyTargetSearchResult(resolvedPoint ? [resolvedPoint.lng, resolvedPoint.lat] : null, shouldAutofillSelection)
  })
}

function searchTargetByKeyword(keyword: string, shouldAutofillSelection: boolean): void {
  const normalizedKeyword = keyword.trim()
  if (!baiduReady.value) {
    targetSearchStatus.value = 'idle'
    return
  }
  if (!normalizedKeyword) {
    searchedTargetCenter.value = null
    targetSearchStatus.value = 'idle'
    syncTargetOverlay()
    return
  }

  searchedTargetCenter.value = null
  syncTargetOverlay()
  const currentSeq = targetSearchSeq.value + 1
  targetSearchSeq.value = currentSeq
  targetSearchStatus.value = 'searching'

  const BMap = window.BMap
  if (!BMap || !mapInstance.value) {
    applyTargetSearchResult(null, shouldAutofillSelection)
    return
  }

  const localSearch = new BMap.LocalSearch(mapInstance.value, {
    pageCapacity: 1,
    onSearchComplete: (results: any) => {
      if (targetSearchSeq.value !== currentSeq) {
        return
      }
      if (typeof localSearch.getStatus === 'function' && localSearch.getStatus() === 0 && results?.getCurrentNumPois?.() > 0) {
        const poi = results.getPoi(0)
        const resolvedPoi = normalizePoint(poi?.point)
        if (resolvedPoi) {
          applyTargetSearchResult([resolvedPoi.lng, resolvedPoi.lat], shouldAutofillSelection)
          return
        }
      }
      fallbackGeocodeTarget(normalizedKeyword, currentSeq, shouldAutofillSelection)
    },
  })
  localSearch.search(normalizedKeyword)
}

function useTargetCenter(): void {
  if (!targetCenter.value) {
    return
  }
  applySelection(targetCenter.value[0], targetCenter.value[1], {
    reverseGeocode: false,
    centerMap: true,
  })
  if (targetKeyword.value) {
    emit('update:address', targetKeyword.value)
  }
}

function locateCurrentPosition(): void {
  if (!geolocation.value) {
    message.warning('百度地图定位不可用')
    return
  }

  geolocation.value.getCurrentPosition(function (this: any, result: any) {
    if (this.getStatus && this.getStatus() !== 0) {
      message.error('浏览器定位失败')
      return
    }
    const point = normalizePoint(result?.point)
    if (!point) {
      message.error('定位成功，但未获取到经纬度')
      return
    }
    applySelection(point.lng, point.lat, {
      reverseGeocode: true,
      centerMap: true,
    })
  }, { enableHighAccuracy: true })
}

async function initializeMap(): Promise<void> {
  if (!hasSdkKey.value || !mapContainerRef.value || baiduReady.value) {
    return
  }

  loading.value = true
  loadError.value = ''
  try {
    const BMap = await loadBaiduMapSdk()
    if (!mapContainerRef.value) {
      return
    }

    const map = new BMap.Map(mapContainerRef.value)
    mapInstance.value = map
    const [lng, lat] = resolvedMapCenter()
    map.centerAndZoom(new BMap.Point(lng, lat), 17)
    map.enableScrollWheelZoom?.(true)
    map.addControl?.(new BMap.ScaleControl())
    map.addControl?.(new BMap.NavigationControl())

    geocoder.value = new BMap.Geocoder()
    geolocation.value = new BMap.Geolocation()

    map.addEventListener('click', (event: any) => {
      if (props.disabled) {
        return
      }
      const point = normalizePoint(event?.point)
      if (!point) {
        return
      }
      applySelection(point.lng, point.lat, {
        reverseGeocode: true,
        centerMap: false,
      })
    })

    baiduReady.value = true
    syncSelectedMarker()
    if (targetKeyword.value) {
      searchTargetByKeyword(targetKeyword.value, !selectedCenter.value)
    } else {
      syncTargetOverlay()
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '地图初始化失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.longitude, props.latitude] as const,
  () => {
    syncSelectedMarker()
    if (selectedCenter.value) {
      centerMap(selectedCenter.value[0], selectedCenter.value[1])
    }
  },
)

watch(
  () => [props.targetAddress, props.targetRange] as const,
  ([targetAddress, targetRange], [previousTargetAddress, previousTargetRange]) => {
    const keyword = targetAddress?.trim() || ''
    const previousKeyword = previousTargetAddress?.trim() || ''
    if (keyword !== previousKeyword || targetRange !== previousTargetRange) {
      searchTargetByKeyword(keyword, !selectedCenter.value)
      return
    }
    syncTargetOverlay()
  },
)

watch(
  () => props.disabled,
  () => {
    if (!selectedMarker.value) {
      return
    }
    if (props.disabled) {
      selectedMarker.value.disableDragging?.()
    } else {
      selectedMarker.value.enableDragging?.()
    }
  },
)

onMounted(() => {
  void initializeMap()
})

onBeforeUnmount(() => {
  if (selectedMarker.value && mapInstance.value) {
    selectedMarker.value.removeEventListener?.('dragend')
    mapInstance.value.removeOverlay(selectedMarker.value)
    selectedMarker.value = null
  }
  removeTargetOverlays()
  if (mapInstance.value) {
    mapInstance.value.clearOverlays?.()
    if (mapContainerRef.value) {
      mapContainerRef.value.innerHTML = ''
    }
    mapInstance.value = null
  }
  geocoder.value = null
  geolocation.value = null
})
</script>

<template>
  <n-space vertical size="small">
    <n-space justify="space-between" align="center" wrap>
      <n-space size="small" wrap>
        <n-button size="small" secondary :disabled="!targetCenter || disabled" @click="useTargetCenter">
          使用目标位置
        </n-button>
        <n-button size="small" secondary :disabled="!baiduReady || disabled" @click="locateCurrentPosition">
          使用当前定位
        </n-button>
      </n-space>
      <n-tag :bordered="false" :type="rangeAlertType">
        {{ props.targetRange != null ? `范围 ${props.targetRange} 米` : '地图选点' }}
      </n-tag>
    </n-space>

    <n-alert v-if="!hasSdkKey" type="warning" :show-icon="false">
      未配置 `VITE_BAIDU_MAP_AK`，地图选点不可用。你仍然可以手工填写经纬度和地址。
    </n-alert>
    <n-alert v-else-if="loadError" type="error" :show-icon="false">
      {{ loadError }}
    </n-alert>
    <n-alert :type="rangeAlertType" :show-icon="false">
      {{ rangeSummary }}
    </n-alert>

    <div ref="mapContainerRef" class="location-picker-map">
      <div v-if="loading" class="location-picker-map__overlay">
        地图加载中...
      </div>
      <div v-else-if="!hasSdkKey || loadError" class="location-picker-map__overlay">
        地图不可用
      </div>
    </div>

    <n-space size="small" wrap>
      <n-text depth="3">已选纬度 {{ props.latitude ?? '--' }}</n-text>
      <n-text depth="3">已选经度 {{ props.longitude ?? '--' }}</n-text>
      <n-text v-if="props.address" depth="3">已选地址 {{ props.address }}</n-text>
    </n-space>
  </n-space>
</template>

<style scoped>
.location-picker-map {
  position: relative;
  min-height: 320px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background:
    radial-gradient(circle at top left, rgba(14, 165, 233, 0.12), transparent 36%),
    linear-gradient(135deg, rgba(248, 250, 252, 1), rgba(226, 232, 240, 0.92));
}

.location-picker-map__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: rgba(15, 23, 42, 0.72);
  text-align: center;
  backdrop-filter: blur(2px);
  z-index: 1;
}
</style>
