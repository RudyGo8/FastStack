/**
 * 存储键名常量
 *
 * @description
 * 统一管理所有 uni.storage 的键名，与 web 端保持一致
 * 命名规则：{分类}_{具体名称}（snake_case）
 */

// 🔐 用户认证相关
export const ACCESS_TOKEN_KEY = 'access_token'
export const REFRESH_TOKEN_KEY = 'refresh_token'
export const REMEMBER_ME_KEY = 'remember_me'

// 📊 数据缓存相关
export const DICT_CACHE_KEY = 'dict_cache'

// 🎨 系统设置相关
export const THEME_KEY = 'theme'
export const THEME_COLOR_KEY = 'themeColor'

// 🛡️ 功能开关相关
export const WATERMARK_KEY = 'watermark_switch'

// 🌍 国际化相关
export const LANG_KEY = 'lang'

// 🎯 角色常量
export const ROLE_ROOT = 'ADMIN'

// 📌 认证相关键集合
export const AUTH_KEYS = {
  ACCESS_TOKEN: ACCESS_TOKEN_KEY,
  REFRESH_TOKEN: REFRESH_TOKEN_KEY,
  REMEMBER_ME: REMEMBER_ME_KEY,
} as const

// 📦 缓存相关键集合
export const CACHE_KEYS = {
  DICT_CACHE: DICT_CACHE_KEY,
} as const

// 🎨 设置相关键集合
export const SETTINGS_KEYS = {
  THEME: THEME_KEY,
  THEME_COLOR: THEME_COLOR_KEY,
  WATERMARK: WATERMARK_KEY,
  LANG: LANG_KEY,
} as const

// 📦 所有存储键的统一集合
export const ALL_STORAGE_KEYS = {
  ...AUTH_KEYS,
  ...CACHE_KEYS,
  ...SETTINGS_KEYS,
} as const
