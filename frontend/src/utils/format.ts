import dayjs from 'dayjs'

export function formatDateTime(value?: string | null): string {
  if (!value) {
    return '--'
  }

  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`
}
