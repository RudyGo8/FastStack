import { request } from "@utils";

const API_PATH = "/ai/rag";

export interface RagDocument {
  filename: string;
  file_type: string;
  chunks: number;
}

export interface RagHit {
  chunk_id: string;
  text: string;
  score: number;
  filename: string;
  file_type: string;
  page_number: number;
  parent_text: string;
}

export interface RagSearchResult {
  hits: RagHit[];
  sources: string[];
}

export interface RagIngestResult {
  filename: string;
  chunks: number;
  parents: number;
}

export const RagAPI = {
  /** 已入库文档清单 */
  documents(tenantId = "") {
    return request<ApiResponse<{ documents: RagDocument[] }>>({
      url: `${API_PATH}/documents`,
      method: "get",
      params: { tenant_id: tenantId },
    });
  },

  /** 文本入库（整篇替换） */
  ingest(data: { filename: string; content: string; file_type?: string; tenant_id?: string }) {
    return request<ApiResponse<RagIngestResult>>({
      url: `${API_PATH}/document`,
      method: "post",
      data,
    });
  },

  /** 混合检索 */
  search(data: { query: string; top_k?: number; tenant_id?: string }) {
    return request<ApiResponse<RagSearchResult>>({
      url: `${API_PATH}/search`,
      method: "post",
      data,
    });
  },

  /** 删除文档及其分块 */
  remove(filename: string, tenantId = "") {
    return request<ApiResponse<{ filename: string; deleted_chunks: number }>>({
      url: `${API_PATH}/document`,
      method: "delete",
      params: { filename, tenant_id: tenantId },
    });
  },
};

export default RagAPI;
