/**
 * CommonUtil 工具方法
 * 提供 deepClone / isString / isObj / isDef / deepMerge 等工具方法
 */
export const CommonUtil = {
  isString(val: unknown): val is string {
    return typeof val === 'string'
  },

  isObj(val: unknown): val is Record<string, any> {
    return val !== null && typeof val === 'object' && !Array.isArray(val)
  },

  isDef(val: unknown): boolean {
    return val !== undefined && val !== null
  },

  /**
   * 深拷贝
   * 优先使用原生 structuredClone（支持 Date/Map/Set/循环引用等），
   * 失败时（如 Vue reactive Proxy 无法被 structuredClone 序列化）回退 JSON 深拷贝。
   */
  deepClone<T>(obj: T): T {
    if (typeof structuredClone === 'function') {
      try {
        return structuredClone(obj)
      }
      catch {
        // structuredClone 无法克隆 Vue reactive Proxy（Pinia $state）等对象，回退 JSON
      }
    }
    return JSON.parse(JSON.stringify(obj)) as T
  },

  deepMerge<T extends Record<string, any>>(target: T, source: Record<string, any>): T {
    const result = { ...target } as Record<string, any>
    for (const key of Object.keys(source)) {
      if (CommonUtil.isObj(source[key]) && CommonUtil.isObj(result[key])) {
        result[key] = CommonUtil.deepMerge(result[key], source[key])
      }
      else {
        result[key] = source[key]
      }
    }
    return result as T
  },
}
