<template>
  <div class="fa-full-height p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>数据源</span>
          <el-button :icon="Refresh" circle :loading="syncing" @click="syncWarehouse"
            >从企业数仓同步</el-button
          >
        </div>
      </template>

      <div v-loading="loading">
        <el-alert type="info" :closable="false" show-icon class="mb-4">
          <template #title
            ><strong>{{
              sourceConnectionConfigured ? "企业数仓连接正常" : "企业数仓尚未配置"
            }}</strong></template
          >
          页面仅展示真实同步记录；未生成快照的数据域会按接入阶段标记为待适配或规划中。
        </el-alert>

        <el-table :data="sources" border stripe>
          <el-table-column prop="label" label="数据域" width="140" />
          <el-table-column label="物理来源视图" min-width="180">
            <template #default="{ row }">{{ row.source_objects?.join("、") || "—" }}</template>
          </el-table-column>
          <el-table-column label="同步状态" width="110">
            <template #default="{ row }"
              ><el-tag :type="getSourceSyncDisplay(row.ingestion_status, row.phase_scope).type">{{
                getSourceSyncDisplay(row.ingestion_status, row.phase_scope).label
              }}</el-tag></template
            >
          </el-table-column>
          <el-table-column prop="latest_snapshot_at" label="最新同步时点" width="180" />
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
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";
import type { SopSourceStatus } from "@/api/module_sop/types";
import { getSourceSyncDisplay } from "../../shared/report-metrics";

defineOptions({ name: "DataSource" });

const loading = ref(false);
const syncing = ref(false);
const sources = ref<SopSourceStatus[]>([]);
const sourceConnectionConfigured = ref(false);

async function loadData() {
  loading.value = true;
  try {
    const status = await SopDataAPI.getDataStatus();
    sources.value = status.data?.data?.sources ?? [];
    sourceConnectionConfigured.value = Boolean(status.data?.data?.source_connection_configured);
  } finally {
    loading.value = false;
  }
}

async function syncWarehouse() {
  syncing.value = true;
  try {
    await SopDataAPI.syncWarehouse();
    ElMessage.success("数仓同步完成");
    await loadData();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "同步失败");
  } finally {
    syncing.value = false;
  }
}

onMounted(loadData);
</script>
