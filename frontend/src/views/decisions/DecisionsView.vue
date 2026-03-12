<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getPendingDecisions } from '@/api/client'
import type { PendingDecisionItem } from '@/types'
import { formatDateTime } from '@/utils/format'

const loading = ref(true)
const decisions = ref<PendingDecisionItem[]>([])

onMounted(async () => {
  decisions.value = await getPendingDecisions()
  loading.value = false
})
</script>

<template>
  <n-space vertical size="large">
    <n-card title="待人工确认" :bordered="false">
      <n-data-table
        :loading="loading"
        :columns="[
          { title: 'ID', key: 'id' },
          { title: '任务 ID', key: 'taskId' },
          { title: '答题记录 ID', key: 'answerRecordId' },
          { title: '原因', key: 'reason' },
          { title: '状态', key: 'status' },
          { title: '创建时间', key: 'createdAt', render: (row: PendingDecisionItem) => formatDateTime(row.createdAt) },
        ]"
        :data="decisions"
        :pagination="false"
      />
    </n-card>

    <n-alert type="warning" show-icon>
      后续这里会接入“确认提交 / 重新答题 / 跳过此题”等人工处理动作。
    </n-alert>
  </n-space>
</template>
