import type { ParamsItem } from '@/api/module_system/params'
import { defineStore } from 'pinia'
import ParamsAPI from '@/api/module_system/params'

/** 强制刷新最小间隔（毫秒），防止短期重复请求 */
const MIN_FETCH_INTERVAL_MS = 5000
/** 请求中标记（模块级变量，不参与持久化，避免请求中断时残留到存储层导致后续加载被卡住） */
let configLoading = false
/** 最近一次成功拉取时间戳 */
let _lastFetchedAt = 0

/**
 * 系统参数状态管理（参考 web 端 config.store.ts）
 *
 * - 从后端 /system/param/info 拉取系统配置（免认证）
 * - 依赖 persistPlugin 按 store id 自动持久化 configData，实现秒开与离线兜底
 * - getConfig 幂等：已加载直接返回；force 强制刷新带 5s 防抖
 */
export const useConfigStore = defineStore('appConfig', {
  state: () => ({
    /** 配置数据，以 config_key 为键 */
    configData: {} as Record<string, ParamsItem>,
    /** 是否已成功加载过配置 */
    isConfigLoaded: false,
  }),

  actions: {
    /**
     * 获取系统配置
     * @param force 是否强制刷新（忽略本地缓存）
     */
    async getConfig(force = false) {
      if (configLoading)
        return

      // 已加载且非强制：直接使用缓存
      if (!force && this.isConfigLoaded)
        return

      // 强制刷新时防抖：间隔内不重复请求
      if (force && Date.now() - _lastFetchedAt < MIN_FETCH_INTERVAL_MS)
        return

      configLoading = true
      try {
        if (force)
          this.configData = {}

        const list = await ParamsAPI.getInitConfig()
        if (!Array.isArray(list)) {
          console.warn('[configStore] getInitConfig 响应非数组', list)
          return
        }
        this.applyConfigList(list)
      }
      catch (error) {
        console.warn('[configStore] 获取系统配置失败', error)
      }
      finally {
        configLoading = false
      }
    },

    /** 将配置列表写入 store（仅收录 config_key 且 config_value 非 undefined 的项） */
    applyConfigList(list: ParamsItem[]) {
      list.forEach((item) => {
        if (item.config_value !== undefined && item.config_key)
          this.configData[item.config_key] = item
      })
      this.isConfigLoaded = true
      _lastFetchedAt = Date.now()
    },
  },
})
