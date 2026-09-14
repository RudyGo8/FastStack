import { http } from '@/http'
import { ContentTypeEnum } from '@/http/tools/enum'

const AUTH_BASE_URL = '/system/auth'

/** 方案提供方 */
export type OAuthProvider = 'wechat' | 'qq' | 'github' | 'gitee'

/**
 * 认证 API
 * 与 web 端 module_system/auth.ts 对齐（完整字段定义）
 */
const AuthAPI = {
  /**
   * 登录
   * @param body 登录表单数据
   * @returns 登录结果
   */
  login(body: LoginFormData): Promise<LoginResult> {
    return http.Post(`${AUTH_BASE_URL}/login`, body, {
      headers: {
        'Content-Type': ContentTypeEnum.FORM_URLENCODED,
      },
      // authRole: 'login'：登录 401（密码错误）按普通错误处理，不触发 token 刷新逻辑
      meta: { ignoreAuth: true, authRole: 'login' },
    })
  },

  /**
   * 刷新令牌
   * @param body 刷新令牌请求体
   * @returns 新的访问令牌
   */
  refreshToken(body: RefreshToekenBody): Promise<LoginResult> {
    // authRole: 'refreshToken'：让 http 层 401 处理器识别刷新请求，自身 401 时不触发刷新逻辑（避免死循环）
    // silent：刷新失败由 http 层统一跳转登录，无需全局 toast
    return http.Post(`${AUTH_BASE_URL}/token/refresh`, body, {
      meta: { ignoreAuth: true, silent: true, authRole: 'refreshToken' },
    })
  },

  /**
   * 获取验证码
   * @returns 验证码信息
   */
  getCaptcha(): Promise<CaptchaInfo> {
    // 添加随机参数防止缓存
    const timestamp = new Date().getTime()
    return http.Get(`${AUTH_BASE_URL}/captcha/get?timestamp=${timestamp}`, { meta: { ignoreAuth: true, authRole: 'visitor' } })
  },

  /**
   * 登出
   * 后端 logout 接口 body 为纯字符串（JWT 原文，Annotated[str, Body]），
   * 需显式 JSON.stringify 使请求体成为合法 JSON 字符串（uni.request 对字符串原样发送）
   * @param token 访问令牌
   */
  logout(token: string): Promise<void> {
    return http.Post(`${AUTH_BASE_URL}/logout`, JSON.stringify(token))
  },

  /**
   * 获取第三方 OAuth 登录跳转 URL
   * @param provider oauth 提供商: wechat / qq / github / gitee
   * @returns 跳转 URL
   */
  getOAuthLoginUrl(provider: OAuthProvider): Promise<{ url: string }> {
    return http.Get(`${AUTH_BASE_URL}/oauth/${provider}/login`, { meta: { ignoreAuth: true, authRole: 'visitor' } })
  },

  /**
   * 滑块验证码完成
   * 后端仅标记 captcha_key 状态为 verified，不校验 x 坐标值（x 为占位字段）
   * @param data 验证数据
   * @param data.captcha_key 验证码 key
   * @param data.x 滑块 x 坐标（占位，后端未使用）
   * @returns 验证结果 { captcha_key, verified }
   */
  completeSliderCaptcha(data: { captcha_key: string, x: number }): Promise<{ captcha_key: string, verified: boolean }> {
    return http.Post(`${AUTH_BASE_URL}/captcha/slider/complete`, data, { meta: { ignoreAuth: true, authRole: 'visitor' } })
  },

  /**
   * 微信小程序登录
   * 前端通过 uni.login 获取 code，后端调用 code2Session 换取 openid 后返回 JWT
   * @param data 微信登录数据
   * @param data.code uni.login 返回的 code
   * @param data.nickname 用户昵称（可选，来自 getUserProfile）
   * @param data.avatar 头像 URL（可选）
   * @returns JWT 登录结果
   */
  wxLogin(data: WxLoginData): Promise<LoginResult> {
    return http.Post(`${AUTH_BASE_URL}/wx-login`, data, { meta: { ignoreAuth: true, authRole: 'visitor' } })
  },

  /**
   * 微信小程序手机号快速登录
   * 用户点击<button open-type="getPhoneNumber">后，回调 e.detail.code 发送给后端
   * 后端通过 getuserphonenumber API 直接获取手机号（2023+ 新方案，无需 AES 解密）
   * @param data 手机号登录数据
   * @param data.code getPhoneNumber 回调返回的动态令牌 code
   * @returns JWT 登录结果
   */
  wxPhoneLogin(data: WxPhoneLoginData): Promise<LoginResult> {
    return http.Post(`${AUTH_BASE_URL}/wx-phone-login`, data, { meta: { ignoreAuth: true, authRole: 'visitor' } })
  },

  /**
   * 生成小程序码
   * 调用后端接口，后端通过微信 getWXACodeUnlimit API 生成无限制小程序码
   * @param data 生成参数
   * @param data.scene 场景参数（最大32字符，如 invite_123）
   * @param data.page 小程序页面路径（可选，默认主页）
   * @param data.width 图片宽度（px，默认 430）
   * @returns 包含 base64 图片 URL 的结果
   */
  generateWxQrCode(data: WxQrCodeParams): Promise<WxQrCodeResult> {
    return http.Post(`${AUTH_BASE_URL}/wx-qrcode/generate`, data)
  },
}

export default AuthAPI

/** 登录表单数据 */
export interface LoginFormData {
  username: string
  password: string
  captcha_key?: string
  captcha?: string
  remember?: boolean
  login_type?: string
}

/** 刷新令牌请求体 */
export interface RefreshToekenBody {
  refresh_token: string
}

/** JWT 响应 */
export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/** 验证码信息（滑块模式：img_base 为空字符串） */
export interface CaptchaInfo {
  enable: boolean
  key: string
  img_base: string
}

/** 微信小程序登录数据 */
export interface WxLoginData {
  code: string
  nickname?: string
  avatar?: string
}

/** 微信手机号登录数据（2023+ 新方案：仅传 code） */
export interface WxPhoneLoginData {
  code: string
}

/** 小程序码生成参数 */
export interface WxQrCodeParams {
  /** 场景值（最大32字符，如 invite_123） */
  scene: string
  /** 目标页面路径（不带 /，如 pages/index/index），为空则默认主页 */
  page?: string
  /** 宽度（px），默认 430，范围 280-1280 */
  width?: number
}

/** 小程序码生成结果 */
export interface WxQrCodeResult {
  /** 小程序码图片 URL（data:image/png;base64,...） */
  url: string
}
