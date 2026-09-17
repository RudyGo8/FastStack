<template>
  <div class="sop-chat fa-full-height">
    <!-- 会话侧栏 -->
    <aside class="chat-side">
      <div class="side-head">
        <div class="side-title"></div>
        <button class="new-btn" @click="newSession">
          <el-icon><Plus /></el-icon>新会话
        </button>
      </div>

      <div class="side-label">会话记录</div>
      <el-scrollbar class="session-scroll">
        <button
          v-for="s in sessions"
          :key="s.session_id"
          class="session-card"
          :class="{ active: s.session_id === currentSessionId }"
          @click="switchSession(s.session_id)"
        >
          <span class="session-icon"
            ><el-icon><ChatLineRound /></el-icon
          ></span>
          <span class="session-body">
            <span class="session-title">{{ s.title || "未命名会话" }}</span>
            <span class="session-meta">
              {{ relTime(s.updated_at) }}
              <i v-if="s.message_count" class="dot" />
              {{ s.message_count }} 条
            </span>
          </span>
          <span class="session-del" @click.stop="removeSession(s.session_id)">
            <el-icon><Delete /></el-icon>
          </span>
        </button>
        <div v-if="!sessions.length" class="side-empty">暂无历史会话</div>
      </el-scrollbar>
    </aside>

    <!-- 对话主区 -->
    <main class="chat-main">
      <div ref="messagesRef" class="messages">
        <!-- 欢迎屏 -->
        <div v-if="!messages.length && !streaming" class="welcome">
          <div class="welcome-logo">🤖</div>
          <h2>👋 Hello，我是智能助手</h2>
          <p>可以问我 SPU 数据口径、预测规则、制度流程或会议纪要相关问题</p>
          <div class="suggest-grid">
            <button
              v-for="s in suggestions"
              :key="s"
              class="suggest-card"
              @click="sendSuggestion(s)"
            >
              <el-icon><ChatDotSquare /></el-icon>
              <span>{{ s }}</span>
            </button>
          </div>
        </div>

        <!-- 消息流 -->
        <template v-for="(msg, i) in messages" :key="i">
          <div class="msg" :class="msg.type">
            <div class="msg-avatar" :class="msg.type">
              <FaSvgIcon v-if="msg.type === 'human'" icon="ri:user-smile-line" />
              <template v-else>🤖</template>
            </div>
            <div class="msg-content">
              <div class="msg-bubble">
                <FaMarkdownRenderer v-if="msg.type !== 'human'" :content="msg.content" />
                <template v-else>{{ msg.content }}</template>
              </div>
              <div v-if="msg.rag_trace && msg.type === 'ai'" class="msg-trace">
                <el-icon><Collection /></el-icon>
                {{
                  msg.rag_trace.tool_used ? `工具调用 · ${msg.rag_trace.tool_name}` : "知识库检索"
                }}
              </div>
            </div>
          </div>
        </template>

        <!-- 流式回复中 -->
        <div v-if="streaming" class="msg ai">
          <div class="msg-avatar ai">🤖</div>
          <div class="msg-content">
            <div class="msg-bubble">
              <div v-if="ragStep" class="stream-step">
                <span class="step-dot" /><span class="step-dot" /><span class="step-dot" />
                {{ ragStep }}
              </div>
              <FaMarkdownRenderer v-if="streamContent" :content="streamContent" />
              <div v-else-if="!ragStep" class="stream-step">
                <span class="step-dot" /><span class="step-dot" /><span class="step-dot" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="composer">
        <div class="composer-box" :class="{ disabled: streaming }">
          <el-input
            v-model="input"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="询问 SPU 数据、预测校验、制度口径或会议纪要…"
            :disabled="streaming"
            resize="none"
            @keydown.enter.exact.prevent="send"
          />
          <button
            class="send-btn"
            :disabled="!input.trim() || streaming"
            :class="{ ready: input.trim() && !streaming }"
            @click="send"
          >
            <el-icon :size="17"><Promotion /></el-icon>
          </button>
        </div>
        <p class="composer-hint">Enter 发送 · 回答由知识库检索生成，请注意核对关键数据</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import {
  ChatDotSquare,
  ChatLineRound,
  Collection,
  Delete,
  Plus,
  Promotion,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import { SopChatAPI, streamChat } from "@/api/module_ai/sop_chat";
import type { SopMessageInfo, SopSessionInfo } from "@/api/module_sop/types";
import FaMarkdownRenderer from "@/components/display/fa-markdown-renderer/index.vue";

defineOptions({ name: "SopChat" });

const suggestions = [
  "C416 最近 6 个月的出库趋势如何？",
  "预测偏差超过 5% 的处理流程是什么？",
  "SPU 与物料编码的映射规则",
];

const sessions = ref<SopSessionInfo[]>([]);
const currentSessionId = ref("default_session");
const messages = ref<Array<SopMessageInfo & { rag_trace?: any }>>([]);
const input = ref("");
const streaming = ref(false);
const streamContent = ref("");
const ragStep = ref("");
const messagesRef = ref<HTMLElement>();
let abortController: AbortController | null = null;

function relTime(iso: string): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour} 小时前`;
  return new Date(iso).toLocaleDateString("zh-CN");
}

function cancelActiveStream() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}

async function loadSessions() {
  const res = await SopChatAPI.getSessionList();
  const list = res.data?.data?.sessions ?? [];
  list.sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  sessions.value = list;
}

function newSession() {
  cancelActiveStream();
  streaming.value = false;
  streamContent.value = "";
  ragStep.value = "";
  currentSessionId.value = `s_${Date.now()}`;
  messages.value = [];
}

async function switchSession(sessionId: string) {
  cancelActiveStream();
  streaming.value = false;
  streamContent.value = "";
  ragStep.value = "";
  currentSessionId.value = sessionId;
  const res = await SopChatAPI.getSessionMessages(sessionId);
  messages.value = res.data?.data?.messages ?? [];
  scrollToBottom();
}

async function removeSession(sessionId: string) {
  await ElMessageBox.confirm("确定删除该会话？", "提示", { type: "warning" });
  await SopChatAPI.deleteSession(sessionId);
  ElMessage.success("会话已删除");
  if (sessionId === currentSessionId.value) newSession();
  await loadSessions();
}

function sendSuggestion(text: string) {
  input.value = text;
  send();
}

async function send() {
  const text = input.value.trim();
  if (!text || streaming.value) return;
  cancelActiveStream();
  input.value = "";
  messages.value.push({ type: "human", content: text, timestamp: new Date().toISOString() });
  streaming.value = true;
  streamContent.value = "";
  ragStep.value = "";
  scrollToBottom();

  const controller = new AbortController();
  abortController = controller;
  try {
    await streamChat(
      text,
      currentSessionId.value,
      {
        onContent: (delta) => {
          streamContent.value += delta;
          scrollToBottom();
        },
        onRagStep: (step) => {
          ragStep.value = step ?? "";
        },
        onError: (msg) => {
          ElMessage.error(msg);
        },
      },
      controller.signal
    );

    if (streamContent.value) {
      messages.value.push({
        type: "ai",
        content: streamContent.value,
        timestamp: new Date().toISOString(),
      });
    }
  } catch (error) {
    if (!(error instanceof DOMException && error.name === "AbortError")) {
      ElMessage.error(error instanceof Error ? error.message : "AI 请求失败，请稍后重试");
    }
  } finally {
    // 旧请求被新会话替换时，不能反向清理新请求的状态。
    if (abortController === controller) {
      abortController = null;
      streaming.value = false;
      ragStep.value = "";
      streamContent.value = "";
      await loadSessions();
      scrollToBottom();
    }
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

onMounted(loadSessions);
onBeforeUnmount(cancelActiveStream);
</script>

<style scoped>
.sop-chat {
  display: flex;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--sop-border, var(--sop-border));
  border-radius: 10px;
  background: var(--sop-surface);
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(20, 27, 45, 0.04);
  margin: 12px;
}

/* ───── 侧栏 ───── */
.chat-side {
  display: flex;
  flex-direction: column;
  width: 264px;
  flex-shrink: 0;
  background: var(--sop-subtle);
  border-right: 1px solid var(--sop-divider);
}
.side-head {
  padding: 16px 14px 12px;
}
.side-title {
  display: flex;
  gap: 10px;
  align-items: center;
}
.side-logo {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  font-size: 20px;
  line-height: 1;
}
.side-title strong {
  display: block;
  color: var(--sop-title);
  font-size: 14px;
}
.side-title small {
  color: var(--sop-faint);
  font-size: 11px;
}
.new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 34px;
  margin-top: 12px;
  border: 1px dashed #bfdbfe;
  border-radius: 8px;
  color: #2563eb;
  background: var(--sop-surface);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.new-btn:hover {
  border-style: solid;
  background: #eff6ff;
}
.side-label {
  padding: 6px 16px;
  color: var(--sop-faint);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
}
.session-scroll {
  flex: 1;
  padding-bottom: 10px;
}
.session-card {
  position: relative;
  display: flex;
  gap: 9px;
  align-items: center;
  width: calc(100% - 12px);
  margin: 0 6px 4px;
  padding: 9px 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s;
}
.session-card:hover {
  background: var(--sop-subtle);
}
.session-card.active {
  background: var(--sop-surface);
  box-shadow: 0 1px 4px rgba(20, 27, 45, 0.08);
}
.session-icon {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  color: var(--sop-faint);
  background: var(--sop-subtle);
  font-size: 14px;
  transition: all 0.12s;
}
.session-card.active .session-icon {
  color: #2563eb;
  background: #dbeafe;
}
.session-body {
  flex: 1;
  min-width: 0;
}
.session-title {
  display: block;
  overflow: hidden;
  color: var(--sop-body);
  font-size: 12.5px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-card.active .session-title {
  color: #1d4ed8;
}
.session-meta {
  display: block;
  margin-top: 2px;
  color: var(--sop-faint);
  font-size: 11px;
}
.session-meta .dot {
  display: inline-block;
  margin: 0 4px;
  border-radius: 50%;
  background: #cbd5e1;
  vertical-align: middle;
}
.session-del {
  flex-shrink: 0;
  padding: 4px;
  border-radius: 5px;
  color: #cbd5e1;
  font-size: 13px;
  opacity: 0;
  transition: all 0.12s;
}
.session-card:hover .session-del {
  opacity: 1;
}
.session-del:hover {
  color: #ef4444;
  background: #fee2e2;
}
.side-empty {
  padding: 24px 0;
  color: var(--sop-faint);
  font-size: 12px;
  text-align: center;
}

/* ───── 主区 ───── */
.chat-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 20px 4px;
  scroll-behavior: smooth;
}

/* 欢迎屏 */
/* 欢迎屏：内容靠上居中（ChatGPT 式），不做垂直居中 */
.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 720px;
  margin: 0 auto;
  padding-top: 8vh;
  text-align: center;
}
.welcome-logo {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  margin-bottom: 10px;
  border-radius: 16px;
  background: linear-gradient(135deg, #eff6ff, #e0e7ff);
  font-size: 30px;
  line-height: 1;
}
.welcome h2 {
  margin: 0 0 6px;
  color: var(--sop-title);
  font-size: 18px;
  font-weight: 700;
}
.welcome p {
  margin: 0 0 18px;
  color: var(--sop-muted);
  font-size: 12.5px;
}
.suggest-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
  width: min(680px, 100%);
}
.suggest-card {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 14px;
  border: 1px solid var(--sop-border);
  border-radius: 10px;
  color: #475569;
  background: var(--sop-surface);
  font-size: 12.5px;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s;
}
.suggest-card .el-icon {
  flex-shrink: 0;
  color: #2563eb;
}
.suggest-card:hover {
  border-color: #93c5fd;
  background: #f8faff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
}

/* 消息 */
.msg {
  display: flex;
  gap: 11px;
  /* 与输入框同宽居中，保持视觉轴线一致 */
  max-width: min(1160px, 100%);
  margin: 0 auto 14px;
}
.msg.human {
  flex-direction: row-reverse;
}
.msg-avatar {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  font-size: 15px;
}
.msg-avatar.human {
  color: #059669;
  background: #ecfdf5;
}
.msg-avatar.ai {
  font-size: 19px;
  line-height: 1;
  background: var(--sop-subtle);
}
.msg-content {
  min-width: 0;
}
.msg-bubble {
  padding: 11px 15px;
  border-radius: 4px 12px 12px 12px;
  background: var(--sop-subtle);
  border: 1px solid var(--sop-divider);
  color: #1e293b;
  font-size: 13.5px;
  line-height: 1.7;
  word-break: break-word;
}
.msg.human .msg-bubble {
  border: none;
  border-radius: 12px 4px 12px 12px;
  color: #fff;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  white-space: pre-wrap;
}
.msg-trace {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--sop-faint);
  background: var(--sop-subtle);
  font-size: 11px;
}

/* 流式状态 */
.stream-step {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--sop-faint);
  font-size: 12px;
}
.step-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #93c5fd;
  animation: pulse 1.2s infinite;
}
.step-dot:nth-child(2) {
  animation-delay: 0.2s;
}
.step-dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

/* 输入区 */
.composer {
  flex-shrink: 0;
  padding: 10px 20px 12px;
  border-top: 1px solid var(--sop-divider);
  background: var(--sop-surface);
}
.composer-box {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  max-width: min(1160px, 100%);
  margin: 0 auto;
  padding: 6px 6px 6px 14px;
  border: 1px solid #dbe4f0;
  border-radius: 14px;
  background: var(--sop-subtle);
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.composer-box:focus-within {
  border-color: #93c5fd;
  background: var(--sop-surface);
  box-shadow: 0 2px 12px rgba(37, 99, 235, 0.1);
}
.composer-box.disabled {
  opacity: 0.6;
}
.composer-box :deep(.el-textarea__inner) {
  border: none;
  padding: 7px 0;
  background: transparent;
  box-shadow: none !important;
  font-size: 13.5px;
  line-height: 1.6;
}
.send-btn {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 9px;
  color: #cbd5e1;
  background: var(--sop-subtle);
  cursor: not-allowed;
  transition: all 0.15s;
}
.send-btn.ready {
  color: #fff;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  cursor: pointer;
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.35);
}
.send-btn.ready:hover {
  transform: translateY(-1px);
}
.send-btn.ready:active {
  transform: translateY(0);
}
.composer-hint {
  max-width: 860px;
  margin: 8px auto 0;
  color: #b6c2d2;
  font-size: 11px;
  text-align: center;
}

@media (max-width: 768px) {
  .chat-side {
    display: none;
  }
}
</style>
