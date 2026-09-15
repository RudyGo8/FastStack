<template>
  <div class="sop-chat fa-full-height">
    <el-container class="h-full">
      <el-aside width="250px" class="session-aside border-r">
        <div class="p-3 flex items-center justify-between">
          <span class="font-bold">会话记录</span>
          <el-button type="primary" size="small" :icon="Plus" @click="newSession">新会话</el-button>
        </div>
        <el-scrollbar class="session-list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: s.session_id === currentSessionId }"
            @click="switchSession(s.session_id)"
          >
            <div class="flex-1 overflow-hidden">
              <div class="truncate text-sm">{{ s.title || s.session_id }}</div>
              <div class="text-xs opacity-60">
                {{ formatTime(s.updated_at) }} · {{ s.message_count }} 条
              </div>
            </div>
            <el-icon class="delete-icon" @click.stop="removeSession(s.session_id)"
              ><Delete
            /></el-icon>
          </div>
          <el-empty v-if="!sessions.length" description="暂无会话" :image-size="60" />
        </el-scrollbar>
      </el-aside>

      <el-container>
        <el-main class="flex flex-col overflow-hidden">
          <div ref="messagesRef" class="messages flex-1 overflow-y-auto px-4">
            <div v-for="(msg, i) in messages" :key="i" class="message-row" :class="msg.type">
              <div class="avatar">{{ msg.type === "human" ? "我" : "AI" }}</div>
              <div class="bubble">
                <FaMarkdownRenderer v-if="msg.type !== 'human'" :content="msg.content" />
                <template v-else>{{ msg.content }}</template>
                <div v-if="msg.rag_trace && msg.type === 'ai'" class="rag-trace">
                  <el-tag size="small" type="info">
                    {{ msg.rag_trace.tool_used ? `工具:${msg.rag_trace.tool_name}` : "知识库" }}
                  </el-tag>
                </div>
              </div>
            </div>
            <div v-if="streaming" class="message-row ai">
              <div class="avatar">AI</div>
              <div class="bubble">
                <span v-if="ragStep" class="text-xs text-gray-400 mr-2">{{ ragStep }}</span>
                <span class="cursor">{{ streamContent ? "" : "….." }}</span>
                <FaMarkdownRenderer v-if="streamContent" :content="streamContent" />
              </div>
            </div>
          </div>

          <div class="input-area border-t p-3">
            <div class="flex gap-2">
              <el-input
                v-model="input"
                type="textarea"
                :autosize="{ minRows: 1, maxRows: 4 }"
                placeholder="询问 SPU 数据、预测校验、制度口径或会议纪要…"
                :disabled="streaming"
                @keydown.enter.exact.prevent="send"
              />
              <el-button type="primary" :loading="streaming" :disabled="!input.trim()" @click="send"
                >发送</el-button
              >
            </div>
          </div>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { Delete, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import { SopChatAPI, streamChat } from "@/api/module_ai/sop_chat";
import type { SopMessageInfo, SopSessionInfo } from "@/api/module_sop/types";
import FaMarkdownRenderer from "@/components/display/fa-markdown-renderer/index.vue";

defineOptions({ name: "SopChat" });

const sessions = ref<SopSessionInfo[]>([]);
const currentSessionId = ref("default_session");
const messages = ref<Array<SopMessageInfo & { rag_trace?: any }>>([]);
const input = ref("");
const streaming = ref(false);
const streamContent = ref("");
const ragStep = ref("");
const messagesRef = ref<HTMLElement>();
let abortController: AbortController | null = null;

const formatTime = (iso: string) =>
  iso ? new Date(iso).toLocaleString("zh-CN", { hour12: false }) : "";

function cancelActiveStream() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}

async function loadSessions() {
  const res = await SopChatAPI.getSessionList();
  sessions.value = res.data?.data?.sessions ?? [];
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

  abortController = new AbortController();
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
    abortController.signal
  );

  abortController = null;
  streaming.value = false;
  ragStep.value = "";
  if (streamContent.value) {
    messages.value.push({
      type: "ai",
      content: streamContent.value,
      timestamp: new Date().toISOString(),
    });
  }
  streamContent.value = "";
  await loadSessions();
  scrollToBottom();
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
.session-aside {
  background: #f8fafc;
  border-color: #e6ebf2;
}
.session-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin: 2px 8px;
  border-radius: 6px;
  cursor: pointer;
}
.session-item:hover {
  background: var(--el-fill-color);
}
.session-item.active {
  color: #2563eb;
  background: #eff6ff;
}
.delete-icon {
  opacity: 0;
  color: var(--el-color-danger);
}
.session-item:hover .delete-icon {
  opacity: 1;
}
.message-row {
  display: flex;
  gap: 10px;
  margin: 12px 0;
}
.message-row.human {
  flex-direction: row-reverse;
}
.message-row .avatar {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  background: #eff6ff;
  color: #2563eb;
}
.message-row.human .avatar {
  background: #ecfdf5;
  color: #059669;
}
.message-row .bubble {
  max-width: 76%;
  padding: 10px 14px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #f8fafc;
  word-break: break-word;
}
.message-row.human .bubble {
  border-color: #bfdbfe;
  background: #eff6ff;
}
.messages {
  background: #fff;
}
.input-area {
  border-color: #e6ebf2;
  background: #fff;
}
.rag-trace {
  margin-top: 6px;
}
.cursor {
  animation: blink 1s infinite;
}
@keyframes blink {
  50% {
    opacity: 0.3;
  }
}
</style>
