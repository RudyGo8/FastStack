<template>
  <div class="fa-full-height sop-memory-page">
    <div class="memory-heading">
      <div>
        <h2>会话记录</h2>
        <p>查看 S&OP 智能问答产生的历史会话与消息</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadSessions">刷新</el-button>
    </div>

    <el-card shadow="never">
      <div class="memory-toolbar">
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索会话标题或会话 ID"
          class="memory-search"
        />
        <span>共 {{ filteredSessions.length }} 个会话</span>
      </div>

      <el-table v-loading="loading" :data="filteredSessions" row-key="session_id" border stripe>
        <el-table-column prop="title" label="会话标题" min-width="220">
          <template #default="{ row }">
            <strong>{{ row.title || "未命名会话" }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="session_id" label="会话 ID" min-width="200" show-overflow-tooltip />
        <el-table-column label="消息数量" width="110" align="center">
          <template #default="{ row }">{{ row.message_count }} 条</template>
        </el-table-column>
        <el-table-column label="最近更新" width="190">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button text type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-hasPerm="'module_sop:chat:delete'"
              text
              type="danger"
              :loading="deletingId === row.session_id"
              @click="removeSession(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无历史会话" /></template>
      </el-table>
    </el-card>

    <el-drawer
      v-model="detailVisible"
      :title="`会话详情 · ${activeSession?.title || activeSession?.session_id || ''}`"
      size="560px"
    >
      <div v-loading="detailLoading" class="message-list">
        <article
          v-for="(message, index) in messages"
          :key="`${message.timestamp}-${index}`"
          class="message-item"
          :class="message.type"
        >
          <header>
            <strong>{{ message.type === "human" ? "用户" : "AI 助手" }}</strong>
            <time>{{ formatTime(message.timestamp) }}</time>
          </header>
          <p>{{ message.content }}</p>
        </article>
        <el-empty v-if="!detailLoading && !messages.length" description="该会话暂无消息" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, ref } from "vue";

import { SopChatAPI } from "@/api/module_ai/sop_chat";
import type { SopMessageInfo, SopSessionInfo } from "@/api/module_sop/types";

defineOptions({ name: "Memory" });

const sessions = ref<SopSessionInfo[]>([]);
const messages = ref<SopMessageInfo[]>([]);
const keyword = ref("");
const loading = ref(false);
const detailLoading = ref(false);
const detailVisible = ref(false);
const deletingId = ref("");
const activeSession = ref<SopSessionInfo | null>(null);

const filteredSessions = computed(() => {
  const query = keyword.value.trim().toLocaleLowerCase();
  if (!query) return sessions.value;
  return sessions.value.filter((session) =>
    `${session.title} ${session.session_id}`.toLocaleLowerCase().includes(query)
  );
});

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function formatTime(value: string): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

async function loadSessions() {
  loading.value = true;
  try {
    const response = await SopChatAPI.getSessionList();
    sessions.value = [...(response.data?.data?.sessions ?? [])].sort((a, b) =>
      (b.updated_at || "").localeCompare(a.updated_at || "")
    );
  } catch (error) {
    sessions.value = [];
    ElMessage.error(errorText(error, "会话记录加载失败"));
  } finally {
    loading.value = false;
  }
}

async function openDetail(row: unknown) {
  const session = row as SopSessionInfo;
  activeSession.value = session;
  messages.value = [];
  detailVisible.value = true;
  detailLoading.value = true;
  try {
    const response = await SopChatAPI.getSessionMessages(session.session_id);
    messages.value = response.data?.data?.messages ?? [];
  } catch (error) {
    ElMessage.error(errorText(error, "会话详情加载失败"));
  } finally {
    detailLoading.value = false;
  }
}

async function removeSession(row: unknown) {
  const session = row as SopSessionInfo;
  try {
    await ElMessageBox.confirm(`确定删除“${session.title || "未命名会话"}”？`, "提示", {
      type: "warning",
    });
  } catch {
    return;
  }

  deletingId.value = session.session_id;
  try {
    await SopChatAPI.deleteSession(session.session_id);
    ElMessage.success("会话已删除");
    if (activeSession.value?.session_id === session.session_id) {
      detailVisible.value = false;
      activeSession.value = null;
      messages.value = [];
    }
    await loadSessions();
  } catch (error) {
    ElMessage.error(errorText(error, "会话删除失败"));
  } finally {
    deletingId.value = "";
  }
}

onMounted(loadSessions);
</script>

<style scoped>
.sop-memory-page {
  padding: 16px;
}

.memory-heading,
.memory-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.memory-heading {
  margin-bottom: 16px;
}

.memory-heading h2 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 20px;
}

.memory-heading p,
.memory-toolbar span {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.memory-toolbar {
  margin-bottom: 14px;
}

.memory-search {
  width: min(360px, 100%);
}

.message-list {
  min-height: 160px;
}

.message-item {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}

.message-item.ai {
  border-left: 3px solid var(--el-color-primary);
}

.message-item.human {
  border-left: 3px solid var(--el-color-success);
}

.message-item header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.message-item time {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.message-item p {
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 720px) {
  .sop-memory-page {
    padding: 10px;
  }

  .memory-heading,
  .memory-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
