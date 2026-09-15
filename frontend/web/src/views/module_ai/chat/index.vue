<template>
  <div class="ai-chat-container fa-full-height sop-page">
    <el-tabs v-model="activeTab" class="ai-chat-tabs" stretch>
      <el-tab-pane label="AI 对话" name="ai">
        <AiChatPanel />
      </el-tab-pane>
      <el-tab-pane label="SOP 问答" name="sop">
        <SopChatPanel />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import AiChatPanel from "./components/AiChatPanel.vue";
import SopChatPanel from "./components/SopChatPanel.vue";

defineOptions({ name: "AiChat" });

const activeTab = ref("sop");
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ai-chat-tabs {
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.ai-chat-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 14px;
  background: #f8fafc;
}
.ai-chat-tabs :deep(.el-tabs__item) {
  height: 40px;
  font-size: 12px;
}
.ai-chat-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ai-chat-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}
.ai-chat-tabs :deep(.el-tab-pane) {
  height: 100%;
}
</style>
