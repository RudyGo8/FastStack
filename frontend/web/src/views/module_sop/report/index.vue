<template>
  <div class="fa-full-height sop-workspace sop-page sop-report-root">
    <section class="sop-report-toolbar">
      <div class="report-brand">
        <span class="report-file-mark"
          ><el-icon><Document /></el-icon
        ></span>
        <div class="brand-info">
          <div class="title-row">
            <strong>青岛玛金智能科技 · S&OP 业务报表</strong>
            <el-tag v-if="report" :type="readinessType" size="small">{{ readinessLabel }}</el-tag>
          </div>
          <span class="sub-desc">历史事实、趋势预测与渠道提报的统一评审视图</span>
        </div>
      </div>

      <div class="report-sub-tabs" aria-label="报告章节">
        <button
          :class="{ active: activeSection === 'overview' }"
          @click="activeSection = 'overview'"
        >
          报告总览
        </button>
        <button :class="{ active: activeSection === 'trend' }" @click="activeSection = 'trend'">
          报表1 · 需求走势
        </button>
        <button :class="{ active: activeSection === 'channel' }" @click="activeSection = 'channel'">
          报表2 · 分渠道预测
          <b v-if="channelMatrix.diffList.length">{{ channelMatrix.diffList.length }}</b>
        </button>
      </div>

      <div class="report-toolbar-actions">
        <label
          ><span>SPU</span
          ><el-select
            v-model="spuCode"
            filterable
            remote
            :remote-method="searchSpus"
            :loading="spuLoading"
            placeholder="选择 SPU"
            class="w-36"
            @change="onSpuChange"
          >
            <el-option
              v-for="s in spuOptions"
              :key="s.spu_code"
              :label="formatSpuLabel(s)"
              :value="s.spu_code"
            /> </el-select
        ></label>
        <label
          ><span>区域</span
          ><el-select
            v-model="region"
            placeholder="全部区域"
            clearable
            class="w-28"
            @change="loadReport"
          >
            <el-option v-for="r in regions" :key="r" :label="r" :value="r" /> </el-select
        ></label>
        <el-button :loading="generating" @click="generateSnapshot">生成快照</el-button>
        <el-button type="primary" :icon="Document" :loading="exporting" @click="exportDocx"
          >导出 Word</el-button
        >
        <el-button type="success" :icon="Download" @click="exportTable">导出 Excel</el-button>
        <el-button :icon="Printer" @click="printPage">打印 / PDF</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </section>

    <article v-if="report" class="sop-report-paper">
      <header class="paper-header">
        <span class="paper-icon"
          ><el-icon><Document /></el-icon
        ></span>
        <h1>{{ spuCode }} S&OP 需求走势与分渠道提报预测报告</h1>
        <p>
          {{ selectedSpuLabel }} · {{ region || "全部区域" }} · 数据时点
          {{ report.as_of_date || asOfDate }}
        </p>
        <div class="paper-callout">
          <el-icon><InfoFilled /></el-icon>
          <span
            ><strong>统计口径与规则：</strong>历史事实按月汇总；未来六个月同时展示 AI
            基线与业务提报；预测偏差绝对值超过 5% 进入关注清单，超过 15% 标记重点偏离。</span
          >
        </div>
      </header>

      <section
        v-show="activeSection === 'overview'"
        class="paper-metrics"
        aria-labelledby="metrics-title"
      >
        <h2 id="metrics-title" class="paper-section-label">核心指标</h2>
        <div class="paper-kpi-grid">
          <article>
            <span>报告周期累计出库</span><strong>{{ fmtNum(metrics.totalOutbound) }} 台</strong
            ><small>实际发货数据</small>
          </article>
          <article>
            <span>报告周期累计激活</span><strong>{{ fmtNum(metrics.totalActivation) }} 台</strong
            ><small>端侧实销数据</small>
          </article>
          <article>
            <span>激活转化比率</span
            ><strong>{{
              metrics.activationRate != null ? `${(metrics.activationRate * 100).toFixed(1)}%` : "—"
            }}</strong
            ><small>由当前业务数据计算</small>
          </article>
          <article>
            <span>预测风险诊断</span
            ><strong class="text-amber">{{ metrics.riskCount }} 项关注</strong
            ><small>确定性规则引擎判定</small>
          </article>
        </div>
      </section>

      <section
        v-show="activeSection === 'overview' || activeSection === 'trend'"
        class="paper-section"
      >
        <div class="paper-section-title">
          <span>报表 1</span>
          <h2>S&OP 需求走势：历史出库/激活与未来六个月 AI 预测、提报预测</h2>
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
          <h2>分渠道提报预测对比（未来六个月）</h2>
        </div>
        <p>黄色单元格表示提报预测与 AI 基线偏差绝对值超过 5%，悬停可查看归因信息。</p>
        <ChannelForecastMatrix :matrix="channelMatrix" />
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

      <section v-show="activeSection === 'overview'" class="paper-section paper-snapshots">
        <div class="paper-section-title">
          <span>归档</span>
          <h2>快照历史</h2>
        </div>
        <el-table :data="snapshots" border size="small" empty-text="尚未生成会议快照">
          <el-table-column prop="spu_code" label="SPU" width="110" />
          <el-table-column prop="as_of_date" label="数据时点" width="120" />
          <el-table-column prop="report_version" label="报告版本" width="130" />
          <el-table-column label="就绪状态" width="150">
            <template #default="{ row }"
              ><el-tag :type="snapshotStatus(row.completeness_status).type" size="small">{{
                snapshotStatus(row.completeness_status).label
              }}</el-tag></template
            >
          </el-table-column>
          <el-table-column prop="record_count" label="记录数" width="90" align="right" />
          <el-table-column prop="generated_at" label="生成时间" min-width="180" />
        </el-table>
      </section>
    </article>

    <section v-else-if="!loading" class="sop-panel report-empty">
      <el-empty description="暂无可生成报告的 SPU 数据" />
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  Document,
  Download,
  InfoFilled,
  Printer,
  Refresh,
  WarningFilled,
} from "@element-plus/icons-vue";
import { computed, onMounted, ref } from "vue";
import * as XLSX from "xlsx";

import { SopDataAPI } from "@/api/module_sop/data";
import { SopReportAPI } from "@/api/module_sop/report";
import type {
  SopFirstPhaseReport,
  SopReportSnapshotSummary,
  SopSpuInfo,
} from "@/api/module_sop/types";
import { Auth } from "@utils";
import { formatSpuLabel } from "../shared/presentation";
import { buildChannelForecastMatrix, buildTrendChartDataset } from "../shared/report-data";
import {
  buildDecisionSummary,
  buildReportMetrics,
  getReportReadinessDisplay,
} from "../shared/report-metrics";
import ChannelForecastMatrix from "../shared/ChannelForecastMatrix.vue";
import SopTrendChart from "../shared/SopTrendChart.vue";
import TrendDataTable from "../shared/TrendDataTable.vue";

defineOptions({ name: "SopReport" });

const activeSection = ref<"overview" | "trend" | "channel">("overview");
const spuCode = ref("");
const spuOptions = ref<SopSpuInfo[]>([]);
const spuLoading = ref(false);
const region = ref("");
const regions = ref<string[]>([]);
const period = ref(new Date().toISOString().slice(0, 7));
const report = ref<SopFirstPhaseReport | null>(null);
const snapshots = ref<SopReportSnapshotSummary[]>([]);
const loading = ref(false);
const generating = ref(false);
const exporting = ref(false);

const metrics = computed(() => buildReportMetrics(report.value));
const decisionSummary = computed(() => buildDecisionSummary(report.value));
const trendData = computed(() => buildTrendChartDataset(report.value));
const channelMatrix = computed(() => buildChannelForecastMatrix(report.value));
const readiness = computed(() =>
  getReportReadinessDisplay(report.value?.completeness_status ?? "not_ready")
);
const readinessType = computed(() =>
  readiness.value.type === "success"
    ? "success"
    : readiness.value.type === "warning"
      ? "warning"
      : "danger"
);
const readinessLabel = computed(() => readiness.value.label);
const selectedSpuLabel = computed(() => {
  const selected = spuOptions.value.find((item) => item.spu_code === spuCode.value);
  return selected ? formatSpuLabel(selected) : spuCode.value || "—";
});
const asOfDate = computed(() => {
  if (!period.value) return "—";
  const [year = 0, month = 0] = period.value.split("-").map(Number);
  return new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10);
});

function fmtNum(value: number | null): string {
  return value === null || value === undefined ? "—" : Number(value).toLocaleString("zh-CN");
}

function snapshotStatus(status: string) {
  return getReportReadinessDisplay(status);
}

async function searchSpus(query: string) {
  if (!query) return;
  spuLoading.value = true;
  try {
    const response = await SopDataAPI.getSpuList({ search: query, limit: 20 });
    spuOptions.value = response.data?.data?.items ?? [];
    const firstSpu = spuOptions.value[0];
    if (!spuCode.value && firstSpu) {
      spuCode.value = firstSpu.spu_code;
      await Promise.all([loadDimensions(), loadReport(), loadSnapshots()]);
    }
  } finally {
    spuLoading.value = false;
  }
}

async function onSpuChange() {
  region.value = "";
  await Promise.all([loadDimensions(), loadReport(), loadSnapshots()]);
}

async function loadDimensions() {
  if (!spuCode.value) return;
  const response = await SopReportAPI.getDimensionOptions(spuCode.value);
  regions.value = response.data?.data?.regions ?? [];
}

async function loadReport() {
  if (!spuCode.value) return;
  loading.value = true;
  try {
    const response = await SopReportAPI.getFirstPhaseReport(spuCode.value, {
      region: region.value,
    });
    report.value = response.data?.data ?? null;
  } finally {
    loading.value = false;
  }
}

async function loadSnapshots() {
  const response = await SopReportAPI.getSnapshotList({
    spu_code: spuCode.value || undefined,
    limit: 20,
  });
  snapshots.value = response.data?.data ?? [];
}

async function loadAll() {
  if (!spuCode.value) return searchSpus("C");
  await Promise.all([loadDimensions(), loadReport(), loadSnapshots()]);
}

async function generateSnapshot() {
  generating.value = true;
  try {
    await SopReportAPI.generateSnapshots({
      spu_code: spuCode.value || undefined,
      as_of_date: asOfDate.value,
    });
    await loadSnapshots();
  } finally {
    generating.value = false;
  }
}

async function exportDocx() {
  if (!spuCode.value) return;
  exporting.value = true;
  try {
    const token = Auth.getAccessToken();
    const base = import.meta.env.VITE_API_BASE_URL || "";
    const response = await fetch(
      `${base}/api/v1/sop/report/spus/${spuCode.value}/export-docx?as_of_date=${asOfDate.value}`,
      {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }
    );
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

function exportTable() {
  const rows = channelMatrix.value.diffList.map((item) => ({
    渠道: item.channel,
    月份: item.month,
    AI预测数量: item.aiQty,
    提报预测数量: item.submitQty,
    差异数量: item.diffQty,
    差异率: `${(item.deviationRatio * 100).toFixed(1)}%`,
    校验维度: item.dimension,
    差异原因: item.reason,
  }));
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(rows), "预测差异");
  XLSX.writeFile(
    workbook,
    `SOP_产销协同业务报表_${spuCode.value || "未选择"}_${period.value}.xlsx`
  );
}

const printPage = () => window.print();

onMounted(() => searchSpus("C"));
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
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(20, 27, 45, 0.04);
}
.report-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 315px;
}
.report-file-mark,
.paper-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #2563eb;
  background: #eff6ff;
}
.report-file-mark {
  width: 34px;
  height: 34px;
  border-radius: 8px;
}
.brand-info {
  min-width: 0;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title-row strong {
  color: #141b2d;
  font-size: 14px;
  white-space: nowrap;
}
.sub-desc {
  display: block;
  margin-top: 2px;
  color: #94a3b8;
  font-size: 10.5px;
}
.report-sub-tabs {
  display: flex;
  gap: 3px;
  padding: 3px;
  border-radius: 6px;
  background: #f1f5f9;
}
.report-sub-tabs button {
  height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 5px;
  color: #64748b;
  background: transparent;
  font-size: 11.5px;
  white-space: nowrap;
}
.report-sub-tabs button.active {
  color: #2563eb;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}
.report-sub-tabs b {
  margin-left: 4px;
  padding: 0 5px;
  border-radius: 999px;
  color: #fff;
  background: #ea580c;
  font-size: 9px;
}
.report-toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
  flex: 1;
  flex-wrap: wrap;
}
.report-toolbar-actions label {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #64748b;
  font-size: 11.5px;
}
.sop-report-paper {
  width: min(1200px, calc(100% - 24px));
  margin: 16px auto 0;
  padding: 34px 46px 48px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 18px rgba(20, 27, 45, 0.04);
}
.paper-header {
  text-align: center;
}
.paper-icon {
  width: 44px;
  height: 44px;
  margin: 0 auto 10px;
  border-radius: 12px;
  font-size: 20px;
}
.paper-header h1 {
  margin: 0;
  color: #141b2d;
  font-size: 24px;
  font-weight: 750;
  letter-spacing: -0.5px;
}
.paper-header > p {
  margin: 5px 0 0;
  color: #64748b;
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
  background: #f8fafc;
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
  color: #94a3b8;
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
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fafbfc;
}
.paper-kpi-grid span,
.paper-kpi-grid small {
  display: block;
  color: #64748b;
  font-size: 11.5px;
}
.paper-kpi-grid strong {
  display: block;
  margin: 5px 0;
  color: #141b2d;
  font-size: 20px;
}
.paper-kpi-grid .text-amber {
  color: #d97706;
}
.paper-section {
  margin-top: 32px;
  padding-top: 25px;
  border-top: 1px dashed #e6ebf2;
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
  color: #141b2d;
  font-size: 16px;
}
.paper-section > p {
  margin: 5px 0 13px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}
.paper-chart-box {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #e6ebf2;
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
  background: #f8fafc;
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
  background: #fffbeb;
  font-size: 11.5px;
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
  .report-brand {
    min-width: 0;
  }
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
    background: #fff;
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
