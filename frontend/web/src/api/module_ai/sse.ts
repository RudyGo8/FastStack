/**
 * SSE 流解析器：从 ReadableStream 解析 Server-Sent Events。
 * 处理跨 chunk 分帧、CRLF 分隔、多行 data:、[DONE] 终止、无尾随空行的末帧。
 */

export interface ChatStreamHandlers {
  onContent?: (delta: string) => void;
  onRagStep?: (step: string | null) => void;
  onTrace?: (trace: Record<string, any> | null) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

function dispatchFrame(dataStr: string, handlers: ChatStreamHandlers, done: { value: boolean }): void {
  if (done.value) return;
  if (dataStr === "[DONE]") {
    done.value = true;
    handlers.onDone?.();
    return;
  }
  try {
    const data = JSON.parse(dataStr);
    if (data.type === "content") handlers.onContent?.(data.content || "");
    else if (data.type === "trace") handlers.onTrace?.(data.rag_trace || null);
    else if (data.type === "rag_step") handlers.onRagStep?.(data.step || null);
    else if (data.type === "error") handlers.onError?.(data.error || data.content || "未知错误");
  } catch {
    // 忽略无法解析的心跳/注释行
  }
}

export async function parseSseStream(
  stream: ReadableStream<Uint8Array>,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const done = { value: false };

  const abortHandler = () => {
    done.value = true;
    reader.cancel().catch(() => {});
  };
  if (signal) {
    if (signal.aborted) {
      done.value = true;
      reader.cancel().catch(() => {});
    } else {
      signal.addEventListener("abort", abortHandler, { once: true });
    }
  }

  try {
    for (;;) {
      const { done: eof, value } = await reader.read();
      if (eof || done.value) break;
      buffer += decoder.decode(value, { stream: true });

      // 按双换行（\n\n 或 \r\n\r\n）切分帧
      let frameEnd: number;
      while ((frameEnd = findFrameEnd(buffer)) >= 0) {
        const frame = buffer.slice(0, frameEnd);
        buffer = buffer.slice(frameEnd + frameSepLen(buffer, frameEnd));
        processFrame(frame, handlers, done);
        if (done.value) break;
      }
    }

    // 末帧：无尾随空行时仍有残余 buffer
    if (!done.value && buffer.trim()) {
      processFrame(buffer, handlers, done);
    }
  } finally {
    if (signal) signal.removeEventListener("abort", abortHandler);
    if (!done.value) {
      done.value = true;
      handlers.onDone?.();
    }
  }
}

function findFrameEnd(buf: string): number {
  const crlf = buf.indexOf("\r\n\r\n");
  const lf = buf.indexOf("\n\n");
  if (crlf >= 0 && (lf < 0 || crlf < lf)) return crlf;
  return lf;
}

function frameSepLen(buf: string, pos: number): number {
  return buf[pos] === "\r" ? 4 : 2;
}

function processFrame(frame: string, handlers: ChatStreamHandlers, done: { value: boolean }): void {
  // 多行 data: 拼接（SSE 规范）
  const dataLines: string[] = [];
  for (const line of frame.split(/\r?\n/)) {
    if (line.startsWith("data: ")) {
      dataLines.push(line.slice(6));
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5));
    }
  }
  if (dataLines.length > 0) {
    dispatchFrame(dataLines.join("\n"), handlers, done);
  }
}
