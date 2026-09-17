import { request } from "@utils";

import type {
  SopDimensionOptions,
  SopFirstPhaseReport,
  SopReportSnapshotDetail,
  SopReportSnapshotSummary,
  SopSnapshotGenerateResponse,
} from "./types";

const API_PATH = "/sop/report";

export interface SopReportQuery {
  as_of_date?: string;
  region?: string;
  channel?: string;
  start_month?: string;
  end_month?: string;
}

export const SopReportAPI = {
  refreshData() {
    return request<ApiResponse<Record<string, any>>>({
      url: `${API_PATH}/refresh`,
      method: "post",
      timeout: 600_000,
    });
  },

  getDimensionOptions(spuCode: string) {
    return request<ApiResponse<SopDimensionOptions>>({
      url: `${API_PATH}/spus/${spuCode}/dimensions`,
      method: "get",
    });
  },

  getFirstPhaseReport(spuCode: string, params: SopReportQuery) {
    return request<ApiResponse<SopFirstPhaseReport>>({
      url: `${API_PATH}/spus/${spuCode}/first-phase`,
      method: "get",
      params,
    });
  },

  generateSnapshots(body?: { spu_code?: string; as_of_date?: string; report_version?: string }) {
    return request<ApiResponse<SopSnapshotGenerateResponse>>({
      url: `${API_PATH}/snapshots/generate`,
      method: "post",
      data: body ?? {},
    });
  },

  getSnapshotList(params: { spu_code?: string; as_of_date?: string; limit?: number }) {
    return request<ApiResponse<SopReportSnapshotSummary[]>>({
      url: `${API_PATH}/snapshots`,
      method: "get",
      params,
    });
  },

  getSnapshotDetail(id: number) {
    return request<ApiResponse<SopReportSnapshotDetail>>({
      url: `${API_PATH}/snapshots/${id}`,
      method: "get",
    });
  },

  getSpuLatestSnapshot(spuCode: string, asOfDate?: string) {
    return request<ApiResponse<SopReportSnapshotDetail>>({
      url: `${API_PATH}/spus/${spuCode}/latest-snapshot`,
      method: "get",
      params: asOfDate ? { as_of_date: asOfDate } : {},
    });
  },
};
