<template>
  <div class="fa-full-height sop-workspace sop-page">
    <div class="sop-page-heading">
      <div>
        <span class="sop-heading-icon">▣</span>
        <div>
          <h2>数据快照</h2>
          <p>每晚 23:00 自动固化 T-1 数据，保证会议口径一致、可溯源</p>
        </div>
      </div>
      <el-button type="primary" :loading="generating" @click="handleGenerate">立即生成快照</el-button>
    </div>

    <section class="sop-panel">
      <div class="toolbar-row">
        <el-select v-model="spuFilter" filterable clearable placeholder="按 SPU 筛选" class="w-44" @change="load">
          <el-option v-for="s in spus" :key="s.spu_code" :label="s.spu_code" :value="s.spu_code" />
        </el-select>
        <el-button :icon="Refresh" circle :loading="loading" @click="load" />
      </div>

      <el-table :data="snapshots" border stripe v-loading="loading">
        <el-table-column prop="spu_code" label="SPU" width="120" />
        <el-table-column prop="as_of_date" label="数据时点" width="120" align="center" />
        <el-table-column prop="report_version" label="版本" min-width="170" />
        <el-table-column label="就绪状态" width="140">
          <template #default="{ row }">
            <el-tag :type="statusDisplay(row.completeness_status).type" size="small">
              {{ statusDisplay(row.completeness_status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="record_count" label="记录数" width="90" align="right" />
        <el-table-column prop="generated_at" label="生成时间" min-width="170" />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无快照记录，点击右上角生成" /></template>
      </el-table>
    </section>

    <el-drawer v-model="detailVisible" :title="`快照详情 · ${activeSnapshot?.spu_code ?? ''}`" size="60%">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" class="mb-4">
          <el-descriptions-item label="SPU">{{ detail.spu_code }}</el-descriptions-item>
          <el-descriptions-item label="数据时点">{{ detail.as_of_date }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ detail.report_version }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ detail.generated_at }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="mb-2">月度实际数据（{{ detail.payload.monthly_actuals?.length ?? 0 }} 条）</h4>
        <el-table :data="(detail.payload.monthly_actuals ?? []).slice(0, 24)" border size="small">
          <el-table-column prop="period" label="月份" width="100" align="center" />
          <el-table-column label="出库（台）" align="right">
            <template #default="{ row }">{{ fmt(row.outbound_qty) }}</template>
          </el-table-column>
          <el-table-column label="激活（台）" align="right">
            <template #default="{ row }">{{ fmt(row.activation_qty) }}</template>
          </el-table-column>
        </el-table>

        <h4 class="mt-4 mb-2">提报预测（{{ detail.payload.forecasts?.length ?? 0 }} 条）</h4>
        <el-table :data="(detail.payload.forecasts ?? []).slice(0, 24)" border size="small">
          <el-table-column label="月份" width="100" align="center">
            <template #default="{ row }">{{ String(row.forecast_month).slice(0, 7) }}</template>
          </el-table-column>
          <el-table-column prop="channel" label="渠道" width="140" />
          <el-table-column label="数量（台）" align="right">
            <template #default="{ row }">{{ fmt(row.forecast_qty) }}</template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";
import { SopReportAPI } from "@/api/module_sop/report";
import type { SopReportSnapshotDetail, SopReportSnapshotSummary, SopSpuInfo } from "@/api/module_sop/types";
import { getReportReadinessDisplay } from "../../shared/report-metrics";

defineOptions({ name: "DataSnapshot" });

const loading = ref(false);
const generating = ref(false);
const snapshots = ref<SopReportSnapshotSummary[]>([]);
const spus = ref<SopSpuInfo[]>([]);
const spuFilter = ref("");
const detailVisible = ref(false);
const detail = ref<SopReportSnapshotDetail | null>(null);
const activeSnapshot = ref<SopReportSnapshotSummary | null>(null);

function statusDisplay(status: string) {
  return getReportReadinessDisplay(status);
}

function fmt(v: unknown): string {
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString("zh-CN") : "—";
}

async function load() {
  loading.value = true;
  try {
    const [spuRes, snapRes] = await Promise.all([
      SopDataAPI.getSpuList({ limit: 200 }),
      SopReportAPI.getSnapshotList({ spu_code: spuFilter.value || undefined, limit: 200 }),
    ]);
    spus.value = spuRes.data?.data?.items ?? [];
    snapshots.value = snapRes.data?.data ?? [];
  } finally {
    loading.value = false;
  }
}

async function handleGenerate() {
  generating.value = true;
  try {
    const res = await SopReportAPI.generateSnapshots({});
    const data = res.data?.data;
    ElMessage.success(`快照生成完成：${data?.generated_count ?? 0} 个 SPU（截至 ${data?.as_of_date ?? "T-1"}）`);
    await load();
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "快照生成失败");
  } finally {
    generating.value = false;
  }
}

async function showDetail(tableRow: unknown) {
  const row = tableRow as SopReportSnapshotSummary;
  activeSnapshot.value = row;
  detailVisible.value = true;
  try {
    const res = await SopReportAPI.getSnapshotDetail(row.id);
    detail.value = res.data?.data ?? null;
  } catch {
    detail.value = null;
  }
}

onMounted(load);
</script>

<style scoped>
.toolbar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
</style>
