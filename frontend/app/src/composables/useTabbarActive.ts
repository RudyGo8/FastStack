import { onShow } from '@dcloudio/uni-app'

/**
 * tab 页 onShow 时同步底部导航高亮。
 * 通过 getCurrentPages 校验当前路由，避免从子页面返回时误触发
 * （子页面返回的中间态路由是子页面自身，不会 emit 到错误 tab）。
 */
export function useTabbarActive(route: string, tabKey: string, onActive?: () => void) {
  onShow(() => {
    const pages = getCurrentPages()
    if (pages.length > 0 && pages[pages.length - 1].route === route) {
      uni.$emit('updateTabbar', tabKey)
      onActive?.()
    }
  })
}
