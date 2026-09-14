import { onShow } from '@dcloudio/uni-app'
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * 页面导航栏标题国际化
 * definePage 的 navigationBarTitleText 是编译期静态文案，
 * 这里在 onShow 时按当前语言动态覆盖标题，语言切换时也能即时刷新。
 */
export function useI18nNavTitle(key: string) {
  const { t, locale } = useI18n()
  function apply() {
    uni.setNavigationBarTitle({ title: t(key) })
  }
  onShow(apply)
  watch(locale, apply)
}
