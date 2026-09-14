import { createI18n } from 'vue-i18n'
import { LANG_KEY } from '@/constants'
import { Storage } from '@/utils/storage'
import enUS from './langs/en.json'
import zhCN from './langs/zh.json'

/** 支持的语言列表 */
export const SUPPORT_LOCALES = ['zh-CN', 'en-US'] as const
export type SupportLocale = typeof SUPPORT_LOCALES[number]

/** 默认语言 */
export const DEFAULT_LOCALE: SupportLocale = 'zh-CN'

/** 从本地存储读取语言偏好（非法值回退默认语言） */
function resolveLocale(): SupportLocale {
  const saved = Storage.get<string>(LANG_KEY)
  return (SUPPORT_LOCALES as readonly string[]).includes(saved || '') ? saved as SupportLocale : DEFAULT_LOCALE
}

/**
 * vue-i18n 实例
 * - legacy: false 使用 Composition API 模式
 * - globalInjection: true 全局注入 $t/$d 等，模板可直接使用 $t（否则会报 Property "$t" is not defined）
 * - 语言偏好持久化于 LANG_KEY，切换后由设置页写入
 */
const i18n = createI18n({
  locale: resolveLocale(),
  legacy: false,
  globalInjection: true,
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export default i18n
