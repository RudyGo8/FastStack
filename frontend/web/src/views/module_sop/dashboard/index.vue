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
              @change="loadReport"
            >
              <el-option v-for="r in regions" :key="r" :label="r" :value="r" /> </el-select
          ></label>
          <label class="sop-filter"
            ><span>计划周期</span
            ><el-date-picker
              v-model="period"
              type="month"
              placeholder="计划周期"
              class="w-36"
              @change="loadReport"
          /></label>
          <div class="sop-filter">
            <span>数据时点</span><b class="sop-date-tag">{{ asOfDate }}</b>
          </div>
        </div>
        <div class="toolbar-actions">
          <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新数据</el-button>
          <el-button type="primary" @click="$router.push('/sop/report')"
            >查看完整会议报告</el-button
          >
        </div>
      </div>
    </section>

    <!-- KPI 卡片 -->
    <el-row :gutter="12" class="kpi-row">
      <el-col :span="5">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header">
            <el-icon><Box /></el-icon><span>管理中的 SPU</span>
          </div>
          <div class="kpi-value">{{ spuTotal || spuOptions.length || "—" }}</div>
          <div class="kpi-note">来自当前主数据接口</div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header">
            <el-icon><Van /></el-icon><span>历史累计出库 (近5年)</span>
          </div>
          <div class="kpi-value">
            {{ fmtNum(kpi.totalOutbound) }} <span class="kpi-unit">台</span>
          </div>
          <div class="kpi-note">
            {{ kpi.actualMonths ? `覆盖 ${kpi.actualMonths} 个历史统计月` : "暂无月度出库记录" }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header">
            <el-icon><Cellphone /></el-icon><span>累计终端激活 (时滞)</span>
          </div>
          <div class="kpi-value">
            {{ fmtNum(kpi.totalActivation) }} <span class="kpi-unit">台</span>
          </div>
          <div class="kpi-note">
            {{ kpi.activationRate ? `出库激活转化比 ${kpi.activationRate}` : "暂无终端激活记录" }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="never" class="kpi-card kpi-purple">
          <div class="kpi-header">
            <el-icon><TrendCharts /></el-icon><span>未来6个月提报总量</span>
          </div>
          <div class="kpi-value text-purple">
            {{ fmtNum(kpi.totalSubmit) }} <span class="kpi-unit">台</span>
          </div>
          <div class="kpi-note">AI基准预测 {{ fmtNum(kpi.totalAi) }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card kpi-warn">
          <div class="kpi-header">
            <el-icon><WarningFilled /></el-icon><span>预测差异项 (>5% 预警)</span>
          </div>
          <div class="kpi-value text-amber">{{ channelMatrix.diffList.length }} 项</div>
          <div class="kpi-note">黄色底色高亮待复核</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 报表1: 走势图 -->
    <section class="sop-panel report-card">
      <div class="report-card-header">
        <div>
          <div class="card-title-row">
            <el-tag type="primary" size="small" class="report-badge">报表 1</el-tag>
            <h3>S&OP 需求走势：历史出库/激活 与 未来6个月AI预测、提报预测</h3>
          </div>
          <p class="card-subtitle">
            SPU: {{ spuCode || "—" }} · 区域: {{ region || "全部区域" }} · 数据来源: 企业数据仓库 ·
            数据时点: {{ asOfDate }} · 历史 60 个月与未来 6 个月滚动预测对比（单位：台）
          </p>
        </div>
        <el-tag type="success" size="small">真实业务数据</el-tag>
      </div>
      <SopTrendChart :data="trendData" />
    </section>

    <!-- 报表2: 分渠道预测对比 -->
    <section class="sop-panel report-card">
      <div class="report-card-header">
        <div>
          <div class="card-title-row">
            <el-tag type="warning" size="small" class="report-badge">报表 2</el-tag>
            <h3>分渠道提报预测对比矩阵（未来6个月）</h3>
          </div>
          <p class="card-subtitle">黄色底色标识偏差 >5% 的单元格，悬停可查看差异幅度与原因批注</p>
        </div>
      </div>
      <ChannelForecastMatrix :matrix="channelMatrix" compact />
    </section>

    <div class="sop-insight-grid">
      <section class="sop-panel sop-insight-panel">
        <div class="sop-section-heading">
          <div>
            <span class="sop-heading-icon warning">!</span>
            <h3>差异明细与原因归因</h3>
          </div>
          <el-tag v-if="channelMatrix.diffList.length" type="warning" size="small"
            >{{ channelMatrix.diffList.length }} 项异常</el-tag
          >
        </div>
        <div v-if="channelMatrix.diffList.length" class="sop-variance-list">
          <article
            v-for="item in channelMatrix.diffList.slice(0, 5)"
            :key="`${item.channel}-${item.month}`"
            class="sop-variance-item"
          >
            <div class="sop-variance-top">
              <strong>{{ item.month }} · {{ item.channel }}</strong>
              <span :class="item.deviationRatio > 0 ? 'up' : 'down'"
                >{{ item.deviationRatio > 0 ? "+" : ""
                }}{{ (item.deviationRatio * 100).toFixed(1) }}%</span
              >
            </div>
            <p>
              <b>{{ item.dimension }}</b
              >{{ item.reason }}
            </p>
          </article>
        </div>
        <el-empty v-else :image-size="52" description="当前筛选范围暂无超过 5% 的预测差异" />
      </section>

      <section class="sop-panel sop-insight-panel">
        <div class="sop-section-heading">
          <div>
            <span class="sop-heading-icon">✓</span>
            <h3>S&OP 规则校验与协同概述</h3>
          </div>
        </div>
        <div class="sop-rule-list">
          <p>
            <strong>统计口径</strong>{{ decisionSummary.supply }} {{ decisionSummary.marketing }}
          </p>
          <p><strong>归因结论</strong>{{ decisionSummary.attribution }}</p>
          <p>
            <strong>差异判定</strong>提报预测与 AI 基线偏差绝对值超过 5% 时进入关注清单，超过 15%
            时标记重点偏离。
          </p>
        </div>
      </section>
    </div>

    <el-empty v-if="!report && !loading" description="选择 SPU 后加载业务数据" />
  </div>
</template>

<script setup lang="ts">
import { Box, Cellphone, Refresh, TrendCharts, Van, WarningFilled } from "@element-plus/icons-vue";
import { computed, onMounted, ref, watch } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";
import { SopReportAPI } from "@/api/module_sop/report";
import type { SopFirstPhaseReport, SopSpuInfo } from "@/api/module_sop/types";
import { formatSpuLabel } from "../shared/presentation";
import { buildChannelForecastMatrix, buildTrendChartDataset } from "../shared/report-data";
import { buildDecisionSummary, buildReportMetrics } from "../shared/report-metrics";
import ChannelForecastMatrix from "../shared/ChannelForecastMatrix.vue";
import SopTrendChart from "../shared/SopTrendChart.vue";

defineOptions({ name: "SopDashboard" });

const spuCode = ref("");
const spuOptions = ref<SopSpuInfo[]>([]);
const spuLoading = ref(false);
const region = ref("");
const regions = ref<string[]>([]);
const channels = ref<string[]>([]);
const period = ref(new Date().toISOString().slice(0, 7));
const report = ref<SopFirstPhaseReport | null>(null);
const loading = ref(false);
const spuTotal = ref(0);

const trendData = computed(() => buildTrendChartDataset(report.value));
const channelMatrix = computed(() => buildChannelForecastMatrix(report.value));
const metrics = computed(() => buildReportMetrics(report.value));
const decisionSummary = computed(() => buildDecisionSummary(report.value));
const asOfDate = computed(() => {
  if (!period.value) return "—";
  const [y = 0, m = 0] = period.value.split("-").map(Number);
  return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
});

const kpi = computed(() => {
  const m = metrics.value;
  return {
    totalOutbound: m.totalOutbound,
    totalActivation: m.totalActivation,
    activationRate: m.activationRate ? `${(m.activationRate * 100).toFixed(1)}%` : null,
    totalSubmit: channelMatrix.value.submitMatrix["合计"]?.reduce((a, b) => a + b, 0) || null,
    totalAi: channelMatrix.value.aiBaselineMatrix["合计"]?.reduce((a, b) => a + b, 0) || null,
    actualMonths: report.value?.monthly_actuals?.length || 0,
  };
});

function fmtNum(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString("zh-CN");
}

async function searchSpus(query: string) {
  if (!query) return;
  spuLoading.value = true;
  try {
    const res = await SopDataAPI.getSpuList({ search: query, limit: 20 });
    spuOptions.value = res.data?.data?.items ?? [];
    spuTotal.value = res.data?.data?.total ?? 0;
    const firstSpu = spuOptions.value[0];
    if (!spuCode.value && firstSpu) {
      spuCode.value = firstSpu.spu_code;
      await Promise.all([loadDimensions(), loadReport()]);
    }
  } finally {
    spuLoading.value = false;
  }
}

function onSpuChange() {
  region.value = "";
  loadDimensions();
  loadReport();
}

async function loadDimensions() {
  if (!spuCode.value) return;
  const res = await SopReportAPI.getDimensionOptions(spuCode.value);
  regions.value = res.data?.data?.regions ?? [];
  channels.value = res.data?.data?.channels ?? [];
}

async function loadReport() {
  if (!spuCode.value) return;
  loading.value = true;
  try {
    const res = await SopReportAPI.getFirstPhaseReport(spuCode.value, {
      region: region.value,
    });
    report.value = res.data?.data ?? null;
  } finally {
    loading.value = false;
  }
}

async function loadAll() {
  loading.value = true;
  try {
    await Promise.all([loadDimensions(), loadReport()]);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  searchSpus("C");
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
}
.toolbar-actions {
  display: flex;
  gap: 8px;
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
  color: #909399;
  font-weight: 500;
}
.kpi-value {
  font-size: 24px;
  font-weight: 750;
  color: #141b2d;
  line-height: 1.15;
  letter-spacing: -0.5px;
}
.kpi-unit {
  font-size: 14px;
  font-weight: 500;
  color: #94a3b8;
}
.kpi-note {
  font-size: 12px;
  color: #94a3b8;
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
  color: #141b2d;
}
.card-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
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
