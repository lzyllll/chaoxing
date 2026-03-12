import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', () => {
  const darkMode = ref(false)
  const collapsed = ref(false)

  const isDark = computed(() => darkMode.value)

  function toggleTheme(): void {
    darkMode.value = !darkMode.value
  }

  function toggleSidebar(): void {
    collapsed.value = !collapsed.value
  }

  return {
    collapsed,
    darkMode,
    isDark,
    toggleSidebar,
    toggleTheme,
  }
})
