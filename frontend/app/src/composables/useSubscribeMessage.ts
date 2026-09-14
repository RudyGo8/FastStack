import { useI18n } from 'vue-i18n'

/**
 * 微信订阅消息 composable
 *
 * 封装 wx.requestSubscribeMessage，在用户操作时请求订阅消息授权。
 * 常见场景：工单状态变更、通知公告发布、系统到期提醒等。
 *
 * 使用前提：
 * 1. 在微信公众平台配置订阅消息模板
 * 2. 将模板 ID 填入此处常量
 * 3. 仅微信小程序端有效
 *
 * @example
 * ```ts
 * const { subscribe } = useSubscribeMessage()
 *
 * // 提交工单时订阅"工单状态变更"通知
 * async function submitTicket() {
 *   await subscribe([TEMPLATE_IDS.TICKET_STATUS])
 *   // ...提交工单
 * }
 * ```
 */

/** 订阅消息模板 ID（在微信公众平台 → 订阅消息中配置） */
export const TEMPLATE_IDS = {
  /** 工单状态变更通知 */
  TICKET_STATUS: '',
  /** 通知公告发布提醒 */
  NOTICE_PUBLISH: '',
  /** 系统到期提醒 */
  SYSTEM_EXPIRY: '',
  /** 工单回复通知 */
  TICKET_REPLY: '',
} as const

/** 订阅消息模板 ID 类型 */
export type TemplateId = keyof typeof TEMPLATE_IDS

/** 订阅结果 */
interface SubscribeResult {
  /** 模板 ID */
  templateId: string
  /** 订阅状态：accept=同意, reject=拒绝, ban=被禁止 */
  status: 'accept' | 'reject' | 'ban' | 'filter'
}

/**
 * 订阅消息 composable
 */
export function useSubscribeMessage() {
  const { t } = useI18n()
  /**
   * 请求订阅消息授权
   *
   * @param templateIds 模板 ID 列表（支持传 key 名称或完整 ID）
   * @returns 订阅结果数组，每项包含模板 ID 和用户选择状态
   */
  async function subscribe(templateIds: Array<TemplateId | string>): Promise<SubscribeResult[]> {
    // #ifdef MP-WEIXIN
    // 将 key 名称解析为实际模板 ID
    const ids = templateIds.map((id) => {
      if (id in TEMPLATE_IDS)
        return TEMPLATE_IDS[id as TemplateId]
      return id
    }).filter(Boolean)

    if (ids.length === 0) {
      console.warn('[useSubscribeMessage] 未配置有效的模板 ID')
      return []
    }

    try {
      const res = await uni.requestSubscribeMessage({
        tmplIds: ids,
      }) as unknown as Record<string, string>

      // 微信返回格式： { [templateId]: 'accept' | 'reject' | 'ban' | 'filter' }
      const results: SubscribeResult[] = ids.map(templateId => ({
        templateId,
        status: res[templateId] as SubscribeResult['status'],
      }))

      // 记录用户选择，可用于后续引导
      const accepted = results.filter(r => r.status === 'accept')
      if (accepted.length > 0)
        console.log(`[useSubscribeMessage] 用户已订阅 ${accepted.length} 个模板`)

      return results
    }
    catch (error) {
      console.error('[useSubscribeMessage] 订阅失败', error)
      return []
    }
    // #endif

    // #ifndef MP-WEIXIN
    return []
    // #endif
  }

  /**
   * 检查订阅消息设置状态
   * 用户可能在设置中关闭了订阅消息，此方法检测并引导用户开启
   *
   * @returns 是否可以发送订阅消息
   */
  async function checkSubscriptionStatus(): Promise<boolean> {
    // #ifdef MP-WEIXIN
    try {
      const settings = await uni.getSetting({})
      const subscription = (settings as any).authSetting?.subscribeMessage
      // 如果用户曾经拒绝过，引导去设置页开启
      if (subscription === false) {
        uni.showModal({
          title: t('common.subscribeTitle'),
          content: t('common.subscribeContent'),
          confirmText: t('common.subscribeGoSetting'),
          success: (res) => {
            if (res.confirm)
              uni.openSetting({})
          },
        })
        return false
      }
      return true
    }
    catch {
      return true
    }
    // #endif

    // #ifndef MP-WEIXIN
    return false
    // #endif
  }

  return {
    subscribe,
    checkSubscriptionStatus,
    TEMPLATE_IDS,
  }
}
