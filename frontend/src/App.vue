<script setup lang="ts">
import { darkTheme, dateZhCN, NConfigProvider, NDialogProvider, NGlobalStyle, NMessageProvider, NNotificationProvider, zhCN } from 'naive-ui'

import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
</script>

<template>
  <n-config-provider :theme="appStore.isDark ? darkTheme : null" :locale="zhCN" :date-locale="dateZhCN">
    <n-global-style />
    <n-dialog-provider>
      <n-notification-provider>
        <n-message-provider>
          <RouterView />
        </n-message-provider>
      </n-notification-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>
