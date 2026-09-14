import { computed, onUnmounted, ref } from 'vue'
import { WATERMARK_KEY } from '@/constants'
import { useUserStore } from '@/store/userStore'
import { Storage } from '@/utils/storage'

/**
 * 小程序水印逻辑（配合 wd-watermark 使用）
 * - 显示条件：本地偏好开启（默认开，由设置页"水印"开关控制）&& 已登录
 * - 水印内容为当前登录用户名（username 优先，回退 name）
 * - 响应式：登录用户 / 设置页开关变更后自动更新（layout 常驻不重挂载，经 uni.$on 同步）
 */
export function useWatermark() {
  const userStore = useUserStore()
  const themeStore = useThemeStore()
  // 兼容历史脏对象 { value }，统一兜底为布尔（wd-switch change 事件参数为对象）
  const stored = Storage.get<boolean | { value: boolean }>(WATERMARK_KEY)
  const localSwitch = ref(typeof stored === 'object' && stored ? Boolean(stored.value) : (stored ?? true))

  const content = computed(() => userStore.userInfo?.username || userStore.userInfo?.name || '')
  const enabled = computed(() => localSwitch.value && !!content.value)
  // 水印文字使用当前主题色，主题色切换后经 wd-watermark 的 props deep watch 自动重绘
  const color = computed(() => themeStore.currentThemeColor.primary)

  // 设置页切换水印开关时同步本地状态（uni.$on 在 H5 / 小程序均可用）
  const onSwitchChange = (value: boolean) => {
    localSwitch.value = value
  }
  uni.$on('updateWatermarkSwitch', onSwitchChange)
  onUnmounted(() => {
    uni.$off('updateWatermarkSwitch', onSwitchChange)
  })

  return { enabled, content, color }
}
