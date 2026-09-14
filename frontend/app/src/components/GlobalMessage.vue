<script lang="ts" setup>
import type { GlobalMessageOptions } from '@/composables/useGlobalMessage'
import { useI18n } from 'vue-i18n'
import { useGlobalMessage } from '@/composables/useGlobalMessage'

const { t } = useI18n()
const { messageOptions, currentPage } = storeToRefs(useGlobalMessage())
const currentPath = getCurrentPath()

watch(() => messageOptions.value, (newVal) => {
  if (newVal && currentPage.value === currentPath) {
    const option: GlobalMessageOptions = { ...newVal }
    uni.showModal({
      title: option.title || '',
      content: option.content || '',
      showCancel: option.showCancel ?? (option.type === 'confirm'),
      confirmText: option.confirmText || t('common.confirm'),
      cancelText: option.cancelText || t('common.cancel'),
      success: (res) => {
        option.success?.({ confirm: res.confirm, cancel: res.cancel })
      },
      fail: (err) => {
        option.fail?.(err)
      },
    })
  }
})
</script>

<script lang="ts">
export default {
  options: {
    virtualHost: true,
    addGlobalClass: true,
    styleIsolation: 'shared',
  },
}
</script>

<template>
  <view />
</template>
