import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/store/userStore'

/**
 * 微信小程序登录 composable
 *
 * 封装 uni.login → 后端换 token 的完整流程。
 * 仅在微信小程序端生效（#ifdef MP-WEIXIN）。
 *
 * @example
 * ```ts
 * const { wxLogin, wxPhoneLogin } = useWxLogin()
 *
 * // 微信一键登录
 * async function handleWxLogin() {
 *   await wxLogin()
 *   uni.reLaunch({ url: '/pages/index/index' })
 * }
 *
 * // 手机号登录（配合 <button open-type="getPhoneNumber">）
 * async function handlePhoneLogin(e) {
 *   if (e.detail.errMsg !== 'getPhoneNumber:ok') return
 *   await wxPhoneLogin(e.detail.code)
 *   uni.reLaunch({ url: '/pages/index/index' })
 * }
 * ```
 */
export function useWxLogin() {
  const { t } = useI18n()
  const userStore = useUserStore()

  /**
   * 微信一键登录
   * 1. uni.login 获取 code
   * 2. 可选获取用户头像昵称（需用户授权）
   * 3. 发送 code 给后端换取 JWT
   */
  async function wxLogin(): Promise<void> {
    // #ifdef MP-WEIXIN
    const { code } = await uni.login({ provider: 'weixin' })
    if (!code)
      throw new Error(t('login.wxAuthFailed'))

    await userStore.wxLogin({ code })
    // #endif

    // #ifndef MP-WEIXIN
    uni.showToast({ title: t('login.wxOnly'), icon: 'none' })
    // #endif
  }

  /**
   * 微信手机号快速登录
   * 配合 <button open-type="getPhoneNumber"> 使用
   * 使用 2023+ 新方案：仅需 getPhoneNumber 回调返回的 code，无需 encryptedData/iv
   *
   * @param phoneCode getPhoneNumber 回调返回的动态令牌（e.detail.code）
   */
  async function wxPhoneLogin(phoneCode: string): Promise<void> {
    // #ifdef MP-WEIXIN
    if (!phoneCode)
      throw new Error(t('login.phoneCodeFailed'))

    await userStore.wxPhoneLogin({ code: phoneCode })
    // #endif

    // #ifndef MP-WEIXIN
    uni.showToast({ title: t('login.wxOnly'), icon: 'none' })
    // #endif
  }

  return {
    wxLogin,
    wxPhoneLogin,
  }
}
