/**
 * 存储工具类
 * 提供localStorage和sessionStorage操作方法
 */

/**
 * localStorage 存储
 */
function set(key: string, value: unknown): void {
  uni.setStorageSync(key, JSON.stringify(value))
}

function get<T>(key: string, defaultValue?: T): T {
  const value = uni.getStorageSync(key)
  if (!value)
    return defaultValue as T

  try {
    return JSON.parse(value)
  }
  catch {
    // 如果解析失败，返回原始字符串
    return value as unknown as T
  }
}

function remove(key: string): void {
  uni.removeStorageSync(key)
}

/**
 * 获取当前存储占用大小（格式化字符串）
 * - H5 遍历 localStorage 累加 UTF-8 字节数
 * - 小程序直接取 uni.getStorageInfoSync 的 currentSize（单位 KB）
 */
function getSize(): string {
  // #ifdef H5
  let bytes = 0
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key)
      bytes += new Blob([key, localStorage.getItem(key) || '']).size
  }
  if (bytes < 1024)
    return `${bytes}B`
  const h5Kb = bytes / 1024
  return h5Kb < 1024 ? `${h5Kb.toFixed(1)}KB` : `${(h5Kb / 1024).toFixed(2)}MB`
  // #endif
  // #ifndef H5
  const info = uni.getStorageInfoSync()
  const mpKb = info.currentSize || 0
  return mpKb < 1 ? `${Math.round(mpKb * 1024)}B` : `${mpKb.toFixed(1)}KB`
  // #endif
}

export const Storage = {
  set,
  get,
  remove,
  getSize,
}
