import { request } from "@utils";

import type { SopDataStatus, SopImportMeta, SopImportResponse, SopSpuListResponse } from "./types";

const API_PATH = "/sop/data";

export const SopDataAPI = {
  getDataStatus() {
    return request<ApiResponse<SopDataStatus>>({
      url: `${API_PATH}/status`,
      method: "get",
    });
  },

  getSpuList(params: { search?: string; limit?: number }) {
    return request<ApiResponse<SopSpuListResponse>>({
      url: `${API_PATH}/spus`,
      method: "get",
      params,
    });
  },

  importSpus(body: { meta: SopImportMeta; rows: Array<Record<string, any>> }) {
    return request<ApiResponse<SopImportResponse>>({
      url: `${API_PATH}/imports/spus`,
      method: "post",
      data: body,
    });
  },

  importSales(body: { meta: SopImportMeta; rows: Array<Record<string, any>> }) {
    return request<ApiResponse<SopImportResponse>>({
      url: `${API_PATH}/imports/sales`,
      method: "post",
      data: body,
    });
  },

  importActivations(body: { meta: SopImportMeta; rows: Array<Record<string, any>> }) {
    return request<ApiResponse<SopImportResponse>>({
      url: `${API_PATH}/imports/activations`,
      method: "post",
      data: body,
    });
  },

  importForecasts(body: { meta: SopImportMeta; rows: Array<Record<string, any>> }) {
    return request<ApiResponse<SopImportResponse>>({
      url: `${API_PATH}/imports/forecasts`,
      method: "post",
      data: body,
    });
  },

  importEvents(body: { meta: SopImportMeta; rows: Array<Record<string, any>> }) {
    return request<ApiResponse<SopImportResponse>>({
      url: `${API_PATH}/imports/events`,
      method: "post",
      data: body,
    });
  },

  syncWarehouse() {
    return request<ApiResponse<Record<string, any>>>({
      url: `${API_PATH}/warehouse/sync`,
      method: "post",
      timeout: 600_000,
    });
  },
};
