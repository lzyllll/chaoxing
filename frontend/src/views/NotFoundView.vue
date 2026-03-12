<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="not-found">
    <n-result status="404" title="页面不存在" description="目标页面未找到，可能路由尚未实现。">
      <template #footer>
        <n-button type="primary" @click="router.push('/')">返回首页</n-button>
      </template>
    </n-result>
  </div>
</template>

<style scoped>
.not-found {
  display: grid;
  min-height: calc(100vh - 120px);
  place-items: center;
}
</style>
