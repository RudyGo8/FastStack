import { request } from "@utils";

const API_PATH = "/monitor/dashboard";

/** 分布统计项 */
export interface DistributionItem {
  name: string;
  value: number;
}

/** 工作台统计卡片数据 */
export interface DashboardStatistics {
  notice_published: number;
  notice_total: number;
  today_logins: number;
  week_logins: number;
  today_operations: number;
  week_operations: number;
}

/** 登录统计数据（近 7 天） */
export interface LoginStatistics {
  os_distribution: DistributionItem[];
  browser_distribution: DistributionItem[];
  location_distribution: DistributionItem[];
}

/** 登录趋势系列 */
export interface LoginTrendSeries {
  name: string;
  data: number[];
}

/** 登录趋势数据（近 7 天，按日聚合） */
export interface LoginTrend {
  dates: string[];
  login_counts: number[];
  location_series: LoginTrendSeries[];
}

/** 操作统计数据（近 7 天） */
export interface OperationStatistics {
  dates: string[];
  type_distribution: DistributionItem[];
  daily_trend: number[];
  module_distribution: DistributionItem[];
}

const DashboardAPI = {
  /** 工作台统计卡片：通知 + 今日/近 7 天登录与操作 */
  getStatistics() {
    return request<ApiResponse<DashboardStatistics>>({
      url: `${API_PATH}/statistics`,
      method: "get",
    });
  },

  /** 近 7 天登录的操作系统 / 浏览器 / 地区分布 */
  getLoginStatistics() {
    return request<ApiResponse<LoginStatistics>>({
      url: `${API_PATH}/login/statistics`,
      method: "get",
    });
  },

  /** 近 7 天登录趋势：每日总次数 + Top 地区每日系列 */
  getLoginTrend() {
    return request<ApiResponse<LoginTrend>>({
      url: `${API_PATH}/login/trend`,
      method: "get",
    });
  },

  /** 近 7 天操作统计：类型分布 / 每日趋势 / 模块分布 */
  getOperationStatistics() {
    return request<ApiResponse<OperationStatistics>>({
      url: `${API_PATH}/operation/statistics`,
      method: "get",
    });
  },
};

export default DashboardAPI;
