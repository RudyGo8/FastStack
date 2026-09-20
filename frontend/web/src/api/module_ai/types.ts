/** AI 模块通用类型定义 */

export interface AiSessionInfo {
  session_id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface AiMessageInfo {
  type: string;
  content: string;
  timestamp: string;
  rag_trace?: Record<string, any> | null;
}

export interface AiDocumentInfo {
  filename: string;
  file_type: string;
  chunk_count: number;
}

export interface AiDocumentChunk {
  chunk_id: string;
  chunk_idx: number;
  text_preview: string;
  file_type: string;
  page_number: number;
  chunk_level: number;
}
