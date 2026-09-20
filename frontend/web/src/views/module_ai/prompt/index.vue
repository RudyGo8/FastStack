<template>
  <div class="fa-full-height p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>Prompt 配置</span>
          <el-button :icon="Refresh" circle :loading="loading" @click="loadConfig" />
        </div>
      </template>

      <div v-loading="loading">
        <el-alert type="info" :closable="false" show-icon class="mb-4">
          <template #title><strong>Prompt 模板管理</strong></template>
          管理系统 Prompt、用户 Prompt 模板。当前为占位页面，后续接入实际配置功能。
        </el-alert>

        <el-empty description="Prompt 配置功能开发中" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { onMounted, ref } from "vue";

defineOptions({ name: "AiPrompt" });

const loading = ref(false);

async function loadConfig() {
  loading.value = true;
  try {
    await new Promise(resolve => setTimeout(resolve, 500));
  } finally {
    loading.value = false;
  }
}

onMounted(loadConfig);
</script>
