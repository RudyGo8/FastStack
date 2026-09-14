/**
 * API 结果枚举 - 与后端 ResultEnum 对应
 *
 * 仅包含业务状态码，HTTP 状态码请使用 {@link HttpStatus}
 */
export enum ResultEnum {
  /** 成功 */
  SUCCESS = 0,
  /** 错误 */
  ERROR = 1,
  /** 异常 */
  EXCEPTION = -1,
  /** 未授权访问 */
  UNAUTHORIZED = 10403,
  /** 令牌已过期 */
  TOKEN_EXPIRED = 10401,
}

/**
 * HTTP 状态码枚举（用于 error.response.status 判断）
 */
export enum HttpStatus {
  SUCCESS = 200,
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  FORBIDDEN = 403,
  NOT_FOUND = 404,
  METHOD_NOT_ALLOWED = 405,
  REQUEST_TIMEOUT = 408,
  INTERNAL_SERVER_ERROR = 500,
  NOT_IMPLEMENTED = 501,
  BAD_GATEWAY = 502,
  SERVICE_UNAVAILABLE = 503,
  GATEWAY_TIMEOUT = 504,
}

/**
 * 内容类型枚举
 */
export enum ContentTypeEnum {
  JSON = 'application/json;charset=UTF-8',
  FORM_URLENCODED = 'application/x-www-form-urlencoded;charset=UTF-8',
  FORM_DATA = 'multipart/form-data;charset=UTF-8',
}

/**
 * 根据状态码，生成对应的错误信息
 * @param status 状态码
 * @returns 错误信息
 */
export function ShowMessage(status: number | string): string {
  let message: string
  switch (status) {
    case 400:
      message = '请求错误(400)'
      break
    case 401:
      message = '未授权，请重新登录(401)'
      break
    case 403:
      message = '拒绝访问(403)'
      break
    case 404:
      message = '请求出错(404)'
      break
    case 408:
      message = '请求超时(408)'
      break
    case 500:
      message = '服务器错误(500)'
      break
    case 501:
      message = '服务未实现(501)'
      break
    case 502:
      message = '网络错误(502)'
      break
    case 503:
      message = '服务不可用(503)'
      break
    case 504:
      message = '网络超时(504)'
      break
    case 505:
      message = 'HTTP版本不受支持(505)'
      break
    default:
      message = `连接出错(${status})!`
  }
  return `${message}，请检查网络或联系管理员！`
}
