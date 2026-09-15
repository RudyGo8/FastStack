<template>
  <div class="fa-full-height p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>数据导入</span>
          <el-button :icon="Refresh" circle :loading="loading" @click="loadData" />
        </div>
      </template>

      <div v-loading="loading">
        <el-alert type="info" :closable="false" show-icon class="mb-4">
          <template #title><strong>数据导入</strong></template>
          支持导入 SPU 主数据、销售事实、激活事实、预测数据与发生事件。仅管理员可操作。
        </el-alert>

        <div class="flex flex-wrap gap-3 mb-4">
          <el-upload v-for="item in importActions" :key="item.domain" :show-file-list="false" :http-request="(option: any) => handleImport(option, item.domain)" accept=".xlsx,.xls">
            <el-button :loading="importing === item.domain">{{ item.label }}</el-button>
          </el-upload>
        </div>

        <el-table v-if="importResults.length" :data="importResults" border>
          <el-table-column prop="time" label="时间" width="180" />
          <el-table-column prop="domain" label="数据域" width="120" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="接受/拒绝" width="120">
            <template #default="{ row }">{{ row.accepted }} / {{ row.rejected }}</template>
          </el-table-column>
          <el-table-column label="质量问题">
            <template #default="{ row }">{{ row.quality_issue_ids?.join("、") || "—" }}</template>
          </el-table-column>
          <el-table-column prop="batch_id" label="批次" min-width="180" />
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
import type { SopImportResponse } from "@/api/module_sop/types";

defineOptions({ name: "DataImport" });

type ImportDomain = "spus" | "sales" | "activations" | "forecasts" | "events";
type ImportLog = SopImportResponse & { time: string };

const loading = ref(false);
const importing = ref<ImportDomain | "">("");
const importResults = ref<ImportLog[]>([]);
const importActions: { domain: ImportDomain; label: string }[] = [
  { domain: "spus", label: "导入 SPU 主数据" },
  { domain: "sales", label: "导入销售事实" },
  { domain: "activations", label: "导入激活事实" },
  { domain: "forecasts", label: "导入预测数据" },
  { domain: "events", label: "导入发生事件" },
];

async function loadData() {
  loading.value = true;
  try {
    await SopDataAPI.getDataStatus();
  } finally {
    loading.value = false;
  }
}

async function handleImport(option: { file: File }, domain: ImportDomain): Promise<void> {
  importing.value = domain;
  try {
    const XLSX = await import("xlsx");
    const workbook = XLSX.read(await option.file.arrayBuffer(), { type: "array" });
    const sheet = workbook.Sheets[workbook.SheetNames[0] ?? ""];
    if (!sheet) throw new Error("表格无有效工作表");
    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: null, raw: false });
    if (!rows.length) throw new Error("表格无数据行");
    const meta = { source_system: "manual_import", source_table: option.file.name, batch_id: `IMP_${Date.now()}`, snapshot_at: new Date().toISOString() };
    const api = { spus: SopDataAPI.importSpus, sales: SopDataAPI.importSales, activations: SopDataAPI.importActivations, forecasts: SopDataAPI.importForecasts, events: SopDataAPI.importEvents }[domain];
    const data = (await api({ meta, rows })).data?.data;
    if (data) {
      importResults.value.unshift({ ...data, time: new Date().toLocaleString("zh-CN", { hour12: false }) });
      ElMessage.success(`导入完成：接受 ${data.accepted} 条，拒绝 ${data.rejected} 条`);
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "导入失败");
  } finally {
    importing.value = "";
  }
}

onMounted(loadData);
</script>
