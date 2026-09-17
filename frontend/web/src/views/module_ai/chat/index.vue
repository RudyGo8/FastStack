<template>
  <div class="ai-chat-container">
    <SopChatPanel />
  </div>
</template>

<script setup lang="ts">
import SopChatPanel from "./components/SopChatPanel.vue";

defineOptions({ name: "AiChat" });
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--sop-bg, #f4f6fa);
}
</style>
