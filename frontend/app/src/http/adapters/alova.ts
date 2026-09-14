import type { Method } from 'alova'
import type { UniappNormalResponse } from '../types'
import AdapterUniapp from '@alova/adapter-uniapp'
import { createAlova } from 'alova'
import VueHook from 'alova/vue'
import AuthAPI from '@/api/module_system/auth'
import { useUserStore } from '@/store/userStore'
import { toLoginPage } from '@/utils/toLoginPage'
import { ContentTypeEnum, HttpStatus, ResultEnum, ShowMessage } from '../tools/enum'

// 配置动态Tag
export const API_DOMAINS = {
  DEFAULT: import.meta.env.VITE_API_BASE_URL || '',
  SECONDARY: import.meta.env.VITE_SERVER_BASEURL_SECONDARY || '',
}

/** 从响应中提取错误消息：优先后端 msg，其次按状态码映射 */
function getErrorMessage(statusCode: number, rawData: any): string {
  return rawData?.msg || rawData?.message || rawData?.error || ShowMessage(statusCode) || `HTTP请求错误[${statusCode}]`
}

/** 登录态失效：清空凭据与用户信息后回登录页（不调用后端注销接口，避免 token 失效后再触发 401） */
function handleAuthExpired(userStore: ReturnType<typeof useUserStore>) {
  userStore.clearAll()
  toLoginPage({ mode: 'reLaunch' })
}

/** 未登录重定向防抖标记：并发请求只跳一次登录页 */
let redirectingToLogin = false

// ===== 401 处理（仿 web 端 utils/http/index.ts）：刷新 token + 并发队列重放 =====

/** token 刷新进行中标记，避免并发 401 触发多次 refresh 请求 */
let isRefreshing = false
let pendingRequests: Array<{
  method: Method
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
}> = []

/** 刷新成功：重放等待队列（重放时 beforeRequest 会自动注入新 token） */
function onRefreshed() {
  const list = pendingRequests
  pendingRequests = []
  list.forEach(({ method, resolve }) => resolve(method.send()))
}

/** 刷新失败：拒绝等待队列 */
function onRefreshFailed() {
  pendingRequests.forEach(({ reject }) => reject(new Error('[认证失效]：登录已过期')))
  pendingRequests = []
}

/**
 * 401 统一处理：
 * - refresh 请求自身 401：抛错交给刷新发起方（避免死循环）
 * - login/visitor 公开请求 401：按普通错误提示
 * - 业务请求 401：首次刷新，并发入队；刷新成功重放，失败清凭据跳登录
 */
async function handleUnauthorized(method: Method, rawData: any): Promise<unknown> {
  const { config } = method
  const userStore = useUserStore()
  const role = config.meta?.authRole
  const message = getErrorMessage(HttpStatus.UNAUTHORIZED, rawData)

  if (role === 'refreshToken')
    throw new Error(message)
  if (role === 'login' || role === 'visitor')
    return throwApiError(message, config)
  if (method.url?.includes('/auth/logout')) {
    handleAuthExpired(userStore)
    throw new Error(message)
  }

  if (!isRefreshing) {
    isRefreshing = true
    try {
      const refreshToken = userStore.getRefreshToken()
      if (!refreshToken)
        throw new Error('[认证失效]：请重新登录')
      const res = await AuthAPI.refreshToken({ refresh_token: refreshToken })
      if (!res?.access_token)
        throw new Error('[认证失效]：登录已过期')
      userStore.setAccessToken(res.access_token)
      if (res.refresh_token)
        userStore.setRefreshToken(res.refresh_token)
      isRefreshing = false
      onRefreshed()
      return method.send()
    }
    catch (error) {
      isRefreshing = false
      onRefreshFailed()
      handleAuthExpired(userStore)
      throw error
    }
  }

  return new Promise((resolve, reject) => {
    pendingRequests.push({ method, resolve, reject })
  })
}

/**
 * alova 请求实例
 */
const alovaInstance = createAlova({
  baseURL: `${API_DOMAINS.DEFAULT}${import.meta.env.VITE_APP_BASE_API || ''}`,
  ...AdapterUniapp(),
  timeout: 10000,
  statesHook: VueHook,

  beforeRequest(method) {
    // 设置默认 Content-Type
    method.config.headers = {
      ContentType: ContentTypeEnum.JSON,
      Accept: 'application/json, text/plain, */*',
      ...method.config.headers,
    }

    const { config } = method
    // 处理动态域名
    if (config.meta?.domain)
      method.baseURL = config.meta.domain

    // 免认证请求（验证码/登录/刷新令牌等）通过 meta.ignoreAuth 标记，统一跳过鉴权
    if (config.meta?.ignoreAuth)
      return

    // 需要认证的请求：校验 token 并注入 Authorization 头
    const userStore = useUserStore()
    const token = userStore.getAccessToken()
    if (!token) {
      // 未登录：清空残留状态并引导到登录页（防抖，避免并发请求重复重定向），并终止请求
      if (!redirectingToLogin) {
        redirectingToLogin = true
        handleAuthExpired(userStore)
        setTimeout(() => {
          redirectingToLogin = false
        }, 1500)
      }
      throw new Error('[请求错误]：未登录')
    }
    method.config.headers.Authorization = `Bearer ${token}`
  },

  responded: {
    // 成功响应拦截：统一处理 HTTP 状态码与业务码，错误统一提示并抛出
    onSuccess: async (response, method) => {
      const { config } = method
      if (config.requestType === 'upload' || config.requestType === 'download')
        return response

      // 普通请求：uniapp adapter 响应结构为 { statusCode, data }（上传/下载已提前返回，此处必为普通请求）
      const { statusCode, data: rawData } = response as unknown as UniappNormalResponse

      // 401：uniapp adapter 对 401 也走成功回调，需在此手动刷新 + 重放
      if (statusCode === HttpStatus.UNAUTHORIZED)
        return handleUnauthorized(method, rawData)
      if (statusCode !== 200)
        return throwApiError(getErrorMessage(statusCode, rawData), config)

      const { code, message, msg, data } = rawData
      if (code !== ResultEnum.SUCCESS) {
        return throwApiError(msg || message || '请求错误', config)
      }
      // 处理成功响应，返回业务数据
      return data
    },

    // 错误响应拦截：覆盖网络/超时等未在 onSuccess 提示过的错误
    onError: (error, method) => {
      const { config } = method
      if (!(error as Error & { __toasted?: boolean })?.__toasted && !config.meta?.silent) {
        if (error.name === 'NetworkError')
          notifyError('网络错误，请检查您的网络连接')
        else if (error.name === 'TimeoutError')
          notifyError('请求超时，请重试')
        else
          notifyError((error as Error)?.message || '请求错误')
      }
      throw error
    },
  },
})

/** 统一错误提示：非组件上下文使用全局 toast（wot-ui wd-toast，挂载于 App.ku.vue） */
function notifyError(message: string) {
  useGlobalToast().error(message || '请求错误')
}

/**
 * 抛出接口错误并统一全局提示
 * 页面无需再单独提取/展示错误信息；meta.silent 可用于内联处理场景（如聊天内联展示）
 */
function throwApiError(message: string, config: { meta?: Record<string, any> }) {
  const err = new Error(message) as Error & { __toasted?: boolean }
  if (!config.meta?.silent) {
    err.__toasted = true
    notifyError(message)
  }
  throw err
}

export const http = alovaInstance
