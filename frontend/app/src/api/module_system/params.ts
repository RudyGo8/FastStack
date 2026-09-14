import { http } from '@/http'

const PARAM_BASE_URL = '/system/param'

/** 系统参数项（与后端 ParamsOutSchema 对齐） */
export interface ParamsItem {
  id: number
  config_name: string
  config_key: string
  config_value: string | null
  config_type: boolean
  status: number
  description?: string | null
  created_time?: string
  update_time?: string
}

/** 系统参数管理 API */
const ParamsAPI = {
  /**
   * 获取初始化缓存参数（系统配置列表）
   *
   * 免认证接口：登录页（无 token）也会调用，需标记 meta.ignoreAuth 跳过鉴权注入
   *
   * @returns 系统配置项列表，config_key 唯一标识
   */
  getInitConfig(): Promise<ParamsItem[]> {
    return http.Get(`${PARAM_BASE_URL}/info`, {
      meta: { ignoreAuth: true },
    })
  },
}

export default ParamsAPI
