import { http } from '@/http'

const MONITOR_BASE = '/monitor'

/**
 * 服务器监控 API
 * 与 web 端 module_monitor/server.ts 对齐（补全完整字段）
 */
export const ServerAPI = {
  getInfo(): Promise<ServerInfo> {
    return http.Get(`${MONITOR_BASE}/server/info`)
  },
}

export interface CpuInfo {
  /** 逻辑核心数 */
  cpu_num: number
  /** user 占用百分比 */
  used: number
  /** system 占用百分比 */
  sys: number
  /** idle 百分比 */
  free: number
}

export interface MemoryInfo {
  total: string
  used: string
  free: string
  usage: number
}

export interface DiskInfo {
  dir_name: string
  sys_type_name: string
  type_name: string
  total: string
  used: string
  free: string
  /** 使用率百分比 */
  usage: number
}

export interface SysInfo {
  computer_ip: string
  computer_name: string
  os_arch: string
  os_name: string
  user_dir: string
}

export interface PyInfo {
  name: string
  version: string
  start_time: string
  run_time: string
  home: string
  memory_total: string
  memory_used: string
  memory_free: string
  /** 进程内存占用率百分比（rss / available） */
  memory_usage: number
}

export interface ServerInfo {
  cpu?: CpuInfo
  mem?: MemoryInfo
  sys?: SysInfo
  py?: PyInfo
  disks?: DiskInfo[]
}
