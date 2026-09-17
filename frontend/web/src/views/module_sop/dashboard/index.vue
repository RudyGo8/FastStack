<template>
  <div class="fa-full-height sop-workspace sop-page">
    <!-- 顶部控制条 -->
    <section class="sop-toolbar" aria-label="计划筛选条件">
      <div class="toolbar-row">
        <div class="toolbar-filters">
          <label class="sop-filter"
            ><span>SPU</span
            ><el-select
              v-model="spuCode"
              filterable
              remote
              :remote-method="searchSpus"
              :loading="spuLoading"
              placeholder="选择 SPU"
              class="w-48"
              :disabled="refreshing"
              @change="onSpuChange"
            >
              <el-option
                v-for="s in spuOptions"
                :key="s.spu_code"
                :label="formatSpuLabel(s)"
                :value="s.spu_code"
              /> </el-select
          ></label>
          <label class="sop-filter"
            ><span>区域</span
            ><el-select
              v-model="region"
              placeholder="全部区域"
              clearable
              class="w-32"
              :disabled="refreshing"
              @change="loadReport"
            >
              <el-option v-for="r in regions" :key="r" :label="r" :value="r" /> </el-select
          ></label>
          <label class="sop-filter"
            ><span>周期</span
            ><el-date-picker
              v-model="dateRange"
              type="monthrange"
              range-separator="至"
              start-placeholder="开始月份"
              end-placeholder="结束月份"
              format="YYYY-MM"
              value-format="YYYY-MM"
              unlink-panels
              class="w-60"
              :disabled="refreshing"
              @change="loadReport"
          /></label>
          <label class="sop-filter"
            ><span>渠道</span
            ><el-select
              v-model="channel"
              placeholder="全部渠道"
              clearable
              class="w-32"
              :disabled="refreshing"
              @change="loadReport"
            >
              <el-option label="全部渠道" value="" />
              <el-option label="海外渠道一部" value="国际渠道销售一部" />
              <el-option label="海外渠道二部" value="国际渠道销售二部" />
              <el-option label="海外电商" value="海外电商" />
              <el-option label="国内渠道" value="国内渠道" />
              <el-option label="国内电商" value="国内电商" />
              <el-option label="其他" value="其他" /> </el-select
          ></label>
          <div class="sop-filter">
            <span>数据时点</span><b class="sop-date-tag">{{ asOfDate }}</b>
          </div>
        </div>
        <div class="toolbar-actions">
          <el-button :icon="Refresh" :loading="loading" @click="refreshFromWarehouse">{{
            refreshing ? "同步数仓中" : "刷新数据"
          }}</el-button>
          <el-button
            type="primary"
            :disabled="loading || !report"
            @click="
              $router.push({
                path: '/sop-analysis/meeting-report',
                query: {
                  ...(spuCode ? { spu: spuCode } : {}),
                  ...(region ? { region } : {}),
                  ...(channel ? { channel } : {}),
                  ...(dateRange?.[0] ? { start: dateRange[0] } : {}),
                  ...(dateRange?.[1] ? { end: dateRange[1] } : {}),
                },
              })
            "
            >查看完整会议报告</el-button
          >
        </div>
      </div>
    </section>

    <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon />
    <p class="kpi-note">
      最后数据同步：{{ lastSyncTime }}{{ refreshing ? " · 正在同步数仓" : "" }}
    </p>

    <!-- KPI 卡片 -->
    <el-row :gutter="12" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header">
            <el-icon><Box /></el-icon><span>管理中的 SPU</span>
          </div>
          <div class="kpi-value">{{ spuTotal || spuOptions.length || "—" }}</div>
          <div class="kpi-note">来自当前主数据接口</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header">
            <el-icon><Van /></el-icon><span>历史累计出库</span>
          </div>
          <div class="kpi-value">
            {{ report ? fmtNum(kpi.totalOutbound) : "—" }} <span class="kpi-unit">台</span>
          </div>
          <div class="kpi-note">
            {{ kpi.actualMonths ? `覆盖 ${kpi.actualMonths} 个历史统计月` : "暂无月度出库记录" }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header">
            <el-icon><Cellphone /></el-icon><span>累计终端激活</span>
          </div>
          <div class="kpi-value">
            {{ report ? fmtNum(kpi.totalActivation) : "—" }} <span class="kpi-unit">台</span>
          </div>
          <div class="kpi-note">
            {{ kpi.actualMonths ? `覆盖 ${kpi.actualMonths} 个月` : "暂无终端激活记录" }}
            {{ kpi.activationRate ? ` · 同期激活/出库比 ${kpi.activationRate}` : "" }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card kpi-purple">
          <div class="kpi-header">
            <el-icon><TrendCharts /></el-icon><span>未来6个月提报总量</span>
          </div>
          <div class="kpi-value text-purple">
            {{ report ? fmtNum(kpi.totalSubmit) : "—" }} <span class="kpi-unit">台</span>
          </div>
          <div class="kpi-note">自 {{ currentMonthLabel }} 起的提报预测汇总</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 报表1: 走势图 -->
    <section class="sop-panel report-card">
      <div class="report-card-header">
        <div>
          <div class="card-title-row">
            <el-tag type="primary" size="small" class="report-badge">报表 1</el-tag>
            <h3>历史出库/激活与未来6个月提报预测</h3>
          </div>
          <p class="card-subtitle">
            SPU: {{ spuCode || "—" }} · 区域: {{ region || "全部区域"
            }}{{ channel ? ` · 渠道: ${channel}` : "" }} · 覆盖 {{ kpi.actualMonths }} 个月历史 ·
            未来 6 个月预测（单位：台）
          </p>
        </div>
        <el-tag v-if="report" type="success" size="small">真实业务数据</el-tag>
      </div>
      <SopTrendChart :data="trendData" />
    </section>

    <!-- 报表2: 分渠道预测对比 -->
    <section class="sop-panel report-card">
      <div class="report-card-header">
        <div>
          <div class="card-title-row">
            <el-tag type="warning" size="small" class="report-badge">报表 2</el-tag>
            <h3>分渠道销售、激活与提报预测</h3>
          </div>
          <p class="card-subtitle">
            实际周期 {{ dateRange?.[0] || "—" }} 至 {{ dateRange?.[1] || "—" }} ·
            实际出库与激活按所选周期展示；提报预测为数据时点所在月起六个月
          </p>
        </div>
      </div>
      <AnnualChannelMatrix :matrix="annualChannelMatrix" />
    </section>

    <el-empty v-if="!report && !loading" description="选择 SPU 后加载业务数据" />
  </div>
</template>

<script setup lang="ts">
import { Box, Cellphone, Refresh, TrendCharts, Van } from "@element-plus/icons-vue";
import { computed, onActivated, onMounted, ref } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";
import { SopReportAPI } from "@/api/module_sop/report";
import type { SopFirstPhaseReport, SopSpuInfo } from "@/api/module_sop/types";
import { formatSpuLabel } from "../shared/presentation";
import {
  buildAnnualChannelMatrix,
  buildTrendChartDataset,
  submittedForecasts,
  reportSyncTime,
} from "../shared/report-data";
import AnnualChannelMatrix from "../shared/AnnualChannelMatrix.vue";
import SopTrendChart from "../shared/SopTrendChart.vue";

defineOptions({ name: "SopDashboard" });

const spuCode = ref("");
const spuOptions = ref<SopSpuInfo[]>([]);
const spuLoading = ref(false);
const region = ref("");
const regions = ref<string[]>([]);
const channels = ref<string[]>([]);
const channel = ref("");
// 默认周期：近 6 个自然月（当月往前推 5 个月的月初起）
const _fmtYM = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const _end = new Date();
const _start = new Date(_end.getFullYear(), _end.getMonth() - 5, 1);
const dateRange = ref<[string, string]>([_fmtYM(_start), _fmtYM(_end)]);
const report = ref<SopFirstPhaseReport | null>(null);
const loading = ref(false);
const refreshing = ref(false);
const loadError = ref("");
let reportRequestId = 0;
let dimensionsRequestId = 0;
let searchRequestId = 0;
const spuTotal = ref(0);

const trendData = computed(() => buildTrendChartDataset(report.value, dateRange.value));
const annualChannelMatrix = computed(() => buildAnnualChannelMatrix(report.value, dateRange.value));
// 数据时点展示真实数据截止日（快照/源表口径），无报告时退回所选周期末月
const asOfDate = computed(() => report.value?.as_of_date || dateRange.value?.[1] || "—");
const currentMonthLabel = computed(() => report.value?.as_of_date.slice(0, 7) || "—");
const lastSyncTime = computed(() => reportSyncTime(report.value));

const kpi = computed(() => {
  const [start = "", end = "9999-12"] = dateRange.value || ["", "9999-12"];

  // 历史数据按所选月份范围动态过滤
  const filteredActuals = (report.value?.monthly_actuals || []).filter(
    (m) => m.period >= start && m.period <= end
  );
  const totalOutbound = filteredActuals.reduce((s, m) => s + (Number(m.outbound_qty) || 0), 0);
  const totalActivation = filteredActuals.reduce((s, m) => s + (Number(m.activation_qty) || 0), 0);

  // 未来6个月提报总量（当前月起共 6 个月）
  const totalSubmit = submittedForecasts(report.value).reduce(
    (sum, item) => sum + Number(item.forecast_qty || 0),
    0
  );
  return {
    totalOutbound,
    totalActivation,
    activationRate:
      totalOutbound > 0 ? `${((totalActivation / totalOutbound) * 100).toFixed(1)}%` : null,
    totalSubmit,
    actualMonths: filteredActuals.length,
  };
});

function fmtNum(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString("zh-CN");
}

async function loadSpuTotal() {
  // KPI"管理中的 SPU"需要全量口径，不能带搜索词或小 limit
  try {
    const res = await SopDataAPI.getSpuList({ limit: 1 });
    spuTotal.value = res.data?.data?.total ?? 0;
  } catch {
    /* KPI 加载失败不打断工作台 */
  }
}

async function searchSpus(query: string) {
  const requestId = ++searchRequestId;
  spuLoading.value = true;
  try {
    const res = await SopDataAPI.getSpuList({ search: query.trim(), limit: 500 });
    if (requestId !== searchRequestId) return;
    spuOptions.value = res.data?.data?.items ?? [];
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

function onSpuChange() {
  region.value = "";
  channel.value = "";
  regions.value = [];
  channels.value = [];
  loadDimensions();
  loadReport();
}

async function loadDimensions() {
  if (!spuCode.value) return;
  const requestId = ++dimensionsRequestId;
  const code = spuCode.value;
  try {
    const response = await SopReportAPI.getDimensionOptions(code);
    if (requestId !== dimensionsRequestId || code !== spuCode.value) return;
    regions.value = response.data?.data?.regions ?? [];
    channels.value = response.data?.data?.channels ?? [];
  } catch {
    // Report loading exposes errors; dimension failures must not restore an older SPU's options.
    if (requestId === dimensionsRequestId) regions.value = [];
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
  await searchSpus("");
  await Promise.all([loadSpuTotal(), loadDimensions(), loadReport()]);
}

let activatedOnce = false;
onActivated(() => {
  if (activatedOnce && spuCode.value && !refreshing.value) loadAll();
  activatedOnce = true;
});

onMounted(() => {
  loadSpuTotal();
  searchSpus("");
});
</script>

<style scoped>
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}
.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.sop-filter {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}
.sop-filter :deep(.el-select),
.sop-filter :deep(.el-date-editor) {
  min-width: 120px;
}

.kpi-card {
  height: 104px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.kpi-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--sop-muted);
  font-weight: 500;
}
.kpi-value {
  font-size: 24px;
  font-weight: 750;
  color: var(--sop-title);
  line-height: 1.15;
  letter-spacing: -0.5px;
}
.kpi-unit {
  font-size: 14px;
  font-weight: 500;
  color: var(--sop-faint);
}
.kpi-note {
  font-size: 12px;
  color: var(--sop-faint);
  margin-top: 4px;
}
.kpi-purple .kpi-value {
  color: #7c3aed;
}
.kpi-warn {
  border-color: #faad14;
}
.kpi-warn .kpi-header {
  color: #faad14;
}
.text-purple {
  color: #7c3aed;
}
.text-amber {
  color: #faad14;
}

.report-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-title-row h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--sop-title);
}
.card-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--sop-muted);
}
.report-badge {
  font-weight: 700;
}

@media (max-width: 1100px) {
  :deep(.el-col-5),
  :deep(.el-col-4) {
    width: 50%;
    max-width: 50%;
    flex: 0 0 50%;
    margin-bottom: 12px;
  }
}

@media (max-width: 680px) {
  :deep(.el-col-5),
  :deep(.el-col-4) {
    width: 100%;
    max-width: 100%;
    flex-basis: 100%;
  }
  .toolbar-actions {
    width: 100%;
  }
}
</style>
