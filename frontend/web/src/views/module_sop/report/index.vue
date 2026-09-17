<template>
  <div class="fa-full-height sop-workspace sop-page sop-report-root">
    <section class="sop-report-toolbar">
      <div class="report-sub-tabs" aria-label="报告章节">
        <button
          :class="{ active: activeSection === 'overview' }"
          @click="activeSection = 'overview'"
        >
          报告总览
        </button>
        <button :class="{ active: activeSection === 'trend' }" @click="activeSection = 'trend'">
          报表1 · 出库/激活与提报预测
        </button>
        <button :class="{ active: activeSection === 'channel' }" @click="activeSection = 'channel'">
          报表2 · 分渠道矩阵
        </button>
      </div>

      <div class="report-toolbar-actions">
        <el-button
          type="primary"
          :icon="Document"
          :loading="exporting"
          :disabled="loading || !report"
          @click="exportDocx"
          >导出 Word</el-button
        >
        <el-button
          :icon="Printer"
          :loading="exporting"
          :disabled="loading || !report"
          @click="exportPdf"
          >导出 PDF</el-button
        >
        <el-button :icon="Refresh" :loading="loading" @click="refreshFromWarehouse">{{
          refreshing ? "同步数仓中" : "刷新"
        }}</el-button>
      </div>
    </section>

    <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon />

    <article v-if="report" class="sop-report-paper">
      <header class="paper-header">
        <span class="paper-icon"
          ><el-icon><Document /></el-icon
        ></span>
        <h1>{{ spuCode }} S&OP 需求走势与分渠道提报预测报告</h1>
        <p>
          {{ selectedSpuLabel }}
          <template v-if="region"> · 区域: {{ region }}</template>
          <template v-if="channel"> · 渠道: {{ channel }}</template>
          <template v-else> · 全部渠道</template>
          · 周期 {{ dateRange[0] }} 至 {{ dateRange[1] }} · 数据时点
          {{ report.as_of_date || asOfDate }} · 最后数据同步 {{ lastSyncTime }}
        </p>
      </header>

      <section
        v-show="activeSection === 'overview'"
        class="paper-metrics"
        aria-labelledby="metrics-title"
      >
        <h2 id="metrics-title" class="paper-section-label">核心指标</h2>
        <div class="paper-kpi-grid">
          <article>
            <span>管理中的 SPU</span>
            <strong>{{ spuTotal || spuOptions.length || "—" }}</strong>
            <small>来自当前主数据接口</small>
          </article>
          <article>
            <span>周期累计出库</span>
            <strong>{{ fmtNum(kpi.totalOutbound) }} 台</strong>
            <small>{{
              kpi.actualMonths ? `覆盖 ${kpi.actualMonths} 个统计月` : "暂无出库记录"
            }}</small>
          </article>
          <article>
            <span>周期累计激活</span>
            <strong>{{ fmtNum(kpi.totalActivation) }} 台</strong>
            <small>{{
              kpi.actualMonths ? `同期激活/出库比 ${kpi.activationRate || "—"}` : "暂无激活记录"
            }}</small>
          </article>
          <article>
            <span>未来6个月提报总量</span>
            <strong class="text-purple">{{ fmtNum(kpi.totalSubmit) }} 台</strong>
            <small>自 {{ currentMonthLabel }} 起</small>
          </article>
        </div>
      </section>

      <section
        v-show="activeSection === 'overview' || activeSection === 'trend'"
        class="paper-section"
      >
        <div class="paper-section-title">
          <span>报表 1</span>
          <h2>历史出库/激活与未来6个月提报预测</h2>
        </div>
        <p>
          展示历史事实走势与未来预测的连续时间轴，数量单位为台；数据缺失保持为空，不以演示值补齐。
        </p>
        <div class="paper-chart-box"><SopTrendChart :data="trendData" /></div>
        <TrendDataTable :points="trendData" />
      </section>

      <section
        v-show="activeSection === 'overview' || activeSection === 'channel'"
        class="paper-section"
      >
        <div class="paper-section-title">
          <span>报表 2</span>
          <h2>分渠道销售、激活与提报预测</h2>
        </div>
        <p>
          实际周期 {{ dateRange?.[0] || "—" }} 至 {{ dateRange?.[1] || "—" }} ·
          实际出库与激活按所选周期展示；提报预测为数据时点所在月起六个月。
        </p>
        <AnnualChannelMatrix :matrix="annualChannelMatrix" />
      </section>

      <section v-show="activeSection === 'overview'" class="paper-section">
        <div class="paper-section-title">
          <span>决策</span>
          <h2>决策摘要与待关注事项</h2>
        </div>
        <div class="paper-decision-grid">
          <article>
            <strong>归因分析</strong>
            <p>{{ decisionSummary.attribution }}</p>
          </article>
          <article>
            <strong>供应侧</strong>
            <p>{{ decisionSummary.supply }}</p>
          </article>
          <article>
            <strong>市场侧</strong>
            <p>{{ decisionSummary.marketing }}</p>
          </article>
        </div>
        <div v-if="report.warnings?.length" class="paper-warning-list">
          <p v-for="warning in report.warnings" :key="warning">
            <el-icon><WarningFilled /></el-icon>{{ warning }}
          </p>
        </div>
      </section>
    </article>

    <section v-else-if="!loading" class="sop-panel report-empty">
      <el-empty description="暂无可生成报告的 SPU 数据" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { Document, InfoFilled, Printer, Refresh, WarningFilled } from "@element-plus/icons-vue";
import { computed, onActivated, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import html2pdf from "html2pdf.js";

import { SopDataAPI } from "@/api/module_sop/data";
import { SopReportAPI } from "@/api/module_sop/report";
import type { SopFirstPhaseReport, SopSpuInfo } from "@/api/module_sop/types";
import { Auth } from "@utils";
import { formatSpuLabel } from "../shared/presentation";
import {
  buildAnnualChannelMatrix,
  buildTrendChartDataset,
  submittedForecasts,
  reportSyncTime,
} from "../shared/report-data";
import { buildDecisionSummary } from "../shared/report-metrics";
import AnnualChannelMatrix from "../shared/AnnualChannelMatrix.vue";
import SopTrendChart from "../shared/SopTrendChart.vue";
import TrendDataTable from "../shared/TrendDataTable.vue";

defineOptions({ name: "SopReport" });

const route = useRoute();

// 与工作台一致的默认周期：近 6 个自然月
const fmtYM = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const now = new Date();
const defaultEnd = fmtYM(now);
const defaultStart = fmtYM(new Date(now.getFullYear(), now.getMonth() - 5, 1));

const activeSection = ref<"overview" | "trend" | "channel">("overview");
const spuCode = ref("");
const spuOptions = ref<SopSpuInfo[]>([]);
const spuLoading = ref(false);
const spuTotal = ref(0);
const region = ref("");
const channel = ref("");
const dateRange = ref<[string, string]>([defaultStart, defaultEnd]);
const report = ref<SopFirstPhaseReport | null>(null);
const loading = ref(false);
const refreshing = ref(false);
const loadError = ref("");
let reportRequestId = 0;
let dimensionsRequestId = 0;
let searchRequestId = 0;
const exporting = ref(false);

const currentMonthLabel = computed(() => report.value?.as_of_date.slice(0, 7) || "—");
const lastSyncTime = computed(() => reportSyncTime(report.value));
const selectedSpuLabel = computed(() => {
  const selected = spuOptions.value.find((item) => item.spu_code === spuCode.value);
  return selected ? formatSpuLabel(selected) : spuCode.value || "—";
});
const asOfDate = computed(() => dateRange.value?.[1] || "—");

const trendData = computed(() => buildTrendChartDataset(report.value, dateRange.value));
const annualChannelMatrix = computed(() => buildAnnualChannelMatrix(report.value, dateRange.value));
const decisionSummary = computed(() => buildDecisionSummary(report.value));

const kpi = computed(() => {
  const [start = "", end = "9999-12"] = dateRange.value || ["", "9999-12"];
  const filteredActuals = (report.value?.monthly_actuals || []).filter(
    (m) => m.period >= start && m.period <= end
  );
  const totalOutbound = filteredActuals.reduce((s, m) => s + (Number(m.outbound_qty) || 0), 0);
  const totalActivation = filteredActuals.reduce((s, m) => s + (Number(m.activation_qty) || 0), 0);
  const totalSubmit = submittedForecasts(report.value).reduce(
    (sum, item) => sum + Number(item.forecast_qty || 0),
    0
  );
  return {
    totalOutbound,
    totalActivation,
    totalSubmit,
    activationRate:
      totalOutbound > 0 ? `${((totalActivation / totalOutbound) * 100).toFixed(1)}%` : null,
    actualMonths: filteredActuals.length,
  };
});

function fmtNum(value: number | null): string {
  return value === null || value === undefined ? "—" : Number(value).toLocaleString("zh-CN");
}

async function loadSpuTotal() {
  const response = await SopDataAPI.getSpuList({ limit: 1 });
  spuTotal.value = response.data?.data?.total ?? 0;
}

async function searchSpus(query: string) {
  const requestId = ++searchRequestId;
  spuLoading.value = true;
  try {
    const response = await SopDataAPI.getSpuList({ search: query.trim(), limit: 500 });
    if (requestId !== searchRequestId) return;
    spuOptions.value = response.data?.data?.items ?? [];

    const firstSpu =
      spuOptions.value.find((item) => item.spu_code === "C416") ?? spuOptions.value[0];
    if (!spuCode.value && firstSpu) {
      spuCode.value = firstSpu.spu_code;
      await Promise.all([loadDimensions(), loadReport()]);
    }
  } finally {
    if (requestId === searchRequestId) spuLoading.value = false;
  }
}

async function loadDimensions() {
  if (!spuCode.value) return;
  const requestId = ++dimensionsRequestId;
  const code = spuCode.value;
  try {
    const response = await SopReportAPI.getDimensionOptions(code);
    if (requestId !== dimensionsRequestId || code !== spuCode.value) return;
    void response;
  } catch {
    // Report loading exposes errors; dimension failures must not restore an older SPU's options.
  }
}

async function loadReport() {
  if (refreshing.value) return;
  const requestId = ++reportRequestId;
  report.value = null;
  loadError.value = "";
  if (!spuCode.value) {
    loading.value = false;
    return;
  }
  loading.value = true;
  const code = spuCode.value;
  const params = {
    region: region.value || "",
    channel: channel.value || "",
    ...(dateRange.value?.[0] ? { start_month: dateRange.value[0] } : {}),
    ...(dateRange.value?.[1] ? { end_month: dateRange.value[1] } : {}),
  };
  try {
    const response = await SopReportAPI.getFirstPhaseReport(code, params);
    if (requestId === reportRequestId) report.value = response.data?.data ?? null;
  } catch {
    if (requestId === reportRequestId) loadError.value = "当前筛选的数据加载失败，请重试";
  } finally {
    if (requestId === reportRequestId) loading.value = false;
  }
}

async function refreshFromWarehouse() {
  if (refreshing.value) return;
  refreshing.value = true;
  ++reportRequestId;
  report.value = null;
  loadError.value = "";
  loading.value = true;
  try {
    await SopReportAPI.refreshData();
  } catch {
    loadError.value = "数据刷新失败，请重试";
    return;
  } finally {
    refreshing.value = false;
    loading.value = false;
  }
  await loadAll();
}

async function loadAll() {
  if (!spuCode.value) return searchSpus("");
  await Promise.all([loadDimensions(), loadReport()]);
}

async function exportDocx() {
  if (!spuCode.value) return;
  exporting.value = true;
  try {
    const token = Auth.getAccessToken();
    const params = new URLSearchParams({
      as_of_date: report.value?.as_of_date || "",
      start_month: dateRange.value[0],
      end_month: dateRange.value[1],
      ...(region.value ? { region: region.value } : {}),
      ...(channel.value ? { channel: channel.value } : {}),
    }).toString();
    const response = await fetch(`/api/v1/sop/report/spus/${spuCode.value}/export-docx?${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error(`导出失败(${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `SOP_会议报告_${spuCode.value}_${asOfDate.value}.docx`;
    anchor.click();
    URL.revokeObjectURL(url);
  } finally {
    exporting.value = false;
  }
}

const exportPdf = async () => {
  const el = document.querySelector(".sop-report-paper") as HTMLElement;
  if (!el) return;
  exporting.value = true;
  try {
    await html2pdf()
      .set({
        margin: [10, 10, 10, 10],
        filename: `SOP_会议报告_${spuCode.value}_${asOfDate.value}.pdf`,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, letterRendering: true },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
      })
      .from(el)
      .save();
  } finally {
    exporting.value = false;
  }
};

async function applyRouteQuery() {
  const presetSpu = (route.query.spu as string)?.trim();
  const presetRegion = (route.query.region as string)?.trim() || "";
  const presetChannel = (route.query.channel as string)?.trim() || "";
  const presetStart = (route.query.start as string)?.trim();
  const presetEnd = (route.query.end as string)?.trim();

  if (presetStart && presetEnd) {
    dateRange.value = [presetStart, presetEnd];
  }
  if (presetSpu) {
    spuCode.value = presetSpu;
    region.value = presetRegion;
    channel.value = presetChannel;
    await searchSpus(presetSpu);
    await Promise.all([loadDimensions(), loadReport()]);
  }
}

let activatedOnce = false;
onActivated(() => {
  if (activatedOnce && spuCode.value && !refreshing.value) loadAll();
  activatedOnce = true;
});

onMounted(() => {
  loadSpuTotal().catch(() => {});
  const presetSpu = (route.query.spu as string)?.trim();
  if (presetSpu) {
    applyRouteQuery();
  } else {
    searchSpus("");
  }
});

// 监听路由参数变化（从工作台跳转时组件可能已挂载，onMounted 不会重触）
watch(() => route.query, applyRouteQuery);
</script>

<style scoped>
.sop-report-root {
  padding-bottom: 48px;
}
.sop-report-toolbar {
  position: sticky;
  top: 0;
  z-index: 12;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 10px 14px;
  border: 1px solid var(--sop-border);
  border-radius: 8px;
  background: var(--sop-surface);
  box-shadow: 0 2px 8px rgba(20, 27, 45, 0.04);
}
.report-sub-tabs {
  display: flex;
  gap: 3px;
  padding: 3px;
  border-radius: 6px;
  background: var(--sop-subtle);
}
.report-sub-tabs button {
  height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 5px;
  color: var(--sop-muted);
  background: transparent;
  font-size: 11.5px;
  white-space: nowrap;
}
.report-sub-tabs button.active {
  color: #2563eb;
  background: var(--sop-surface);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}
.report-toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
  flex: 1;
  flex-wrap: wrap;
}
.sop-report-paper {
  width: min(1200px, calc(100% - 24px));
  margin: 16px auto 0;
  padding: 34px 46px 48px;
  border: 1px solid var(--sop-border);
  border-radius: 8px;
  background: var(--sop-surface);
  box-shadow: 0 4px 18px rgba(20, 27, 45, 0.04);
}
.paper-header {
  text-align: center;
}
.paper-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin: 0 auto 10px;
  border-radius: 12px;
  color: #2563eb;
  background: #eff6ff;
  font-size: 20px;
}
.paper-header h1 {
  margin: 0;
  color: var(--sop-title);
  font-size: 24px;
  font-weight: 750;
  letter-spacing: -0.5px;
}
.paper-header > p {
  margin: 5px 0 0;
  color: var(--sop-muted);
  font-size: 12px;
}
.paper-callout {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 18px;
  padding: 11px 14px;
  border-left: 4px solid #2563eb;
  border-radius: 0 6px 6px 0;
  color: #475569;
  background: var(--sop-subtle);
  text-align: left;
  font-size: 12px;
  line-height: 1.65;
}
.paper-callout .el-icon {
  flex: 0 0 auto;
  margin-top: 3px;
  color: #2563eb;
}
.paper-section-label {
  margin: 0 0 8px;
  color: var(--sop-faint);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.paper-metrics {
  margin-top: 20px;
}
.paper-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.paper-kpi-grid article {
  padding: 13px 15px;
  border: 1px solid var(--sop-border);
  border-radius: 8px;
  background: var(--sop-subtle);
}
.paper-kpi-grid span,
.paper-kpi-grid small {
  display: block;
  color: var(--sop-muted);
  font-size: 11.5px;
}
.paper-kpi-grid strong {
  display: block;
  margin: 5px 0;
  color: var(--sop-title);
  font-size: 20px;
}
.paper-kpi-grid .text-purple {
  color: #7c3aed;
}
.paper-section {
  margin-top: 32px;
  padding-top: 25px;
  border-top: 1px dashed var(--sop-border);
}
.paper-section-title {
  display: flex;
  align-items: center;
  gap: 9px;
}
.paper-section-title > span {
  padding: 2px 7px;
  border-radius: 4px;
  color: #fff;
  background: #2563eb;
  font-size: 10px;
  font-weight: 700;
}
.paper-section-title h2 {
  margin: 0;
  color: var(--sop-title);
  font-size: 16px;
}
.paper-section > p {
  margin: 5px 0 13px;
  color: var(--sop-muted);
  font-size: 12px;
  line-height: 1.6;
}
.paper-chart-box {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid var(--sop-border);
  border-radius: 8px;
}
.paper-decision-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.paper-decision-grid article {
  padding: 12px;
  border-radius: 7px;
  background: var(--sop-subtle);
}
.paper-decision-grid strong {
  color: #1e293b;
  font-size: 12px;
}
.paper-decision-grid p {
  margin: 5px 0 0;
  color: #475569;
  font-size: 11.5px;
  line-height: 1.65;
}
.paper-warning-list {
  margin-top: 12px;
}
.paper-warning-list p {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 6px 0 0;
  padding: 8px 10px;
  border: 1px solid #fef3c7;
  border-radius: 6px;
  color: #92400e;
  background: var(--sop-surface);
  font-size: 11.5px;
}
.paper-snapshots {
  margin-top: 32px;
}
.report-empty {
  margin-top: 14px;
}

@media (max-width: 1350px) {
  .sop-report-toolbar {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .report-toolbar-actions {
    justify-content: flex-start;
  }
}
@media (max-width: 800px) {
  .sop-report-paper {
    width: 100%;
    padding: 24px 18px 36px;
  }
  .paper-header h1 {
    font-size: 20px;
  }
  .paper-kpi-grid,
  .paper-decision-grid {
    grid-template-columns: 1fr 1fr;
  }
  .report-sub-tabs {
    width: 100%;
    overflow-x: auto;
  }
}
@media (max-width: 520px) {
  .paper-kpi-grid,
  .paper-decision-grid {
    grid-template-columns: 1fr;
  }
}

@media print {
  .sop-report-toolbar {
    display: none;
  }
  .sop-report-root {
    padding: 0;
    background: var(--sop-surface);
  }
  .sop-report-paper {
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    box-shadow: none;
  }
  .paper-section {
    break-inside: avoid;
  }
}
</style>
