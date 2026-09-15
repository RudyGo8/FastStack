import { request } from "@utils";

import type { SopDocumentChunk, SopDocumentInfo } from "@/api/module_sop/types";

const API_PATH = "/sop/documents";

export interface SopUploadResult {
  filename: string;
  success?: boolean;
  chunks_processed: number;
  message: string;
}

export interface SopBatchUploadResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: SopUploadResult[];
  message: string;
}

export const SopDocumentAPI = {
  list() {
    return request<ApiResponse<{ documents: SopDocumentInfo[] }>>({
      url: `${API_PATH}/list`,
      method: "get",
    });
  },

  upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<ApiResponse<SopUploadResult>>({
      url: `${API_PATH}/upload`,
      method: "post",
      data: form,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  batchUpload(files: File[]) {
    const form = new FormData();
    for (const file of files) {
      form.append("files", file);
    }
    return request<ApiResponse<SopBatchUploadResponse>>({
      url: `${API_PATH}/batch-upload`,
      method: "post",
      data: form,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  getChunks(filename: string) {
    return request<ApiResponse<{ filename: string; chunks: SopDocumentChunk[] }>>({
      url: `${API_PATH}/${encodeURIComponent(filename)}/chunks`,
      method: "get",
    });
  },

  delete(filename: string) {
    return request<ApiResponse<{ filename: string; chunks_deleted: number; message: string }>>({
      url: `${API_PATH}/${encodeURIComponent(filename)}`,
      method: "delete",
    });
  },
};
