import { request, Auth } from "@utils";

import type { SopMessageInfo, SopSessionInfo } from "@/api/module_sop/types";
import { parseSseStream, type ChatStreamHandlers } from "./sse";

const API_PATH = "/sop/chat";

export type { ChatStreamHandlers };

export const SopChatAPI = {
  getSessionList() {
    return request<ApiResponse<{ sessions: SopSessionInfo[] }>>({
      url: `${API_PATH}/sessions`,
      method: "get",
    });
  },

  getSessionMessages(sessionId: string) {
    return request<ApiResponse<{ messages: SopMessageInfo[] }>>({
      url: `${API_PATH}/sessions/${encodeURIComponent(sessionId)}`,
      method: "get",
    });
  },

  deleteSession(sessionId: string) {
    return request<ApiResponse<{ session_id: string; message: string }>>({
      url: `${API_PATH}/sessions/${encodeURIComponent(sessionId)}`,
      method: "delete",
    });
  },
};

/** 一次性消费 POST /chat/stream 的 SSE 流，支持取消。 */
export async function streamChat(
  message: string,
  sessionId: string,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = Auth.getAccessToken();
  const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "text/event-stream" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const base = import.meta.env.VITE_API_BASE_URL || "";
  const res = await fetch(`${base}/api/v1${API_PATH}/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });
  if (!res.ok || !res.body) {
    handlers.onError?.(`请求失败(${res.status})`);
    handlers.onDone?.();
    return;
  }

  await parseSseStream(res.body, handlers, signal);
}
