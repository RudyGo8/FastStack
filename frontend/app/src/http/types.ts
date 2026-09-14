/**
 * 在 uniapp 的 RequestOptions 和 UploadFileOption 基础上，添加自定义参数
 */
export type CustomRequestOptions = UniApp.RequestOptions & {
  query?: Record<string, any>
  /** 出错时是否隐藏错误提示 */
  hideErrorToast?: boolean
} & UniApp.UploadFileOption // 添加uni.uploadFile参数类型

/** 主要提供给 openapi-ts-request 生成的代码使用 */
export type CustomRequestOptions_ = Omit<CustomRequestOptions, 'url'>

export interface HttpRequestResult<T> {
  promise: Promise<T>
  requestTask: UniApp.RequestTask
}

// 通用响应格式（兼容 msg + message 字段）
export interface IResponse<T = any> {
  code: number
  data: T
  msg: string
  message?: string
  status_code: number
  success: boolean
  [key: string]: any // 允许额外属性
}

// 分页请求参数
export interface PageParams {
  page: number
  pageSize: number
  [key: string]: any
}

/**
 * uniapp adapter 普通请求（非上传/下载）的响应结构
 * 对应 UniNamespace.RequestSuccessCallbackResult
 */
export interface UniappNormalResponse {
  statusCode: number
  data: IResponse
}
