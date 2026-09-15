<template>
  <div class="fa-full-height p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>数据质量</span>
          <el-button :icon="Refresh" circle :loading="loading" @click="loadData" />
        </div>
      </template>

      <div v-loading="loading">
        <el-alert type="warning" :closable="false" show-icon class="mb-4">
          <template #title><strong>数据质量监控</strong></template>
          当前存在 {{ openIssues }} 个未解决的数据质量问题。请联系管理员处理。
        </el-alert>

        <el-table :data="sources" border stripe>
          <el-table-column prop="label" label="数据域" width="140" />
          <el-table-column label="同步状态" width="110">
            <template #default="{ row }"
              ><el-tag :type="getSourceSyncDisplay(row.ingestion_status, row.phase_scope).type">{{
                getSourceSyncDisplay(row.ingestion_status, row.phase_scope).label
              }}</el-tag></template
            >
          </el-table-column>
          <el-table-column prop="max_business_date" label="最新业务日期" width="130" />
          <el-table-column prop="record_count" label="记录数" width="100" />
          <el-table-column prop="note" label="说明" min-width="220" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { onMounted, ref } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";
import type { SopSourceStatus } from "@/api/module_sop/types";
import { getSourceSyncDisplay } from "../../shared/report-metrics";

defineOptions({ name: "DataQuality" });

const loading = ref(false);
const sources = ref<SopSourceStatus[]>([]);
const openIssues = ref(0);

async function loadData() {
  loading.value = true;
  try {
    const status = await SopDataAPI.getDataStatus();
    sources.value = status.data?.data?.sources ?? [];
    openIssues.value = status.data?.data?.open_quality_issues ?? 0;
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>
