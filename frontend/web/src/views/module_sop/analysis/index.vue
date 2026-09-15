<template>
  <div class="fa-full-height sop-workspace sop-page">
    <!-- 顶部控制条 -->
    <section class="sop-toolbar" aria-label="预测校验筛选条件">
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
            ><span>渠道</span
            ><el-select
              v-model="channel"
              placeholder="全部渠道"
              clearable
              class="w-32"
              @change="loadReport"
            >
              <el-option v-for="c in channels" :key="c" :label="c" :value="c" /> </el-select
          ></label>
          <label class="sop-filter"
            ><span>校验周期</span
            ><el-date-picker
              v-model="period"
              type="month"
              placeholder="校验周期"
              class="w-36"
              @change="loadReport"
          /></label>
          <div class="sop-filter">
            <span>数据时点</span><b class="sop-date-tag">{{ asOfDate }}</b>
          </div>
        </div>
        <div class="toolbar-actions">
          <el-button :icon="Refresh" :loading="loading" @click="loadReport">刷新校验结果</el-button>
        </div>
      </div>
    </section>

    <!-- 校验统计卡片 -->
    <el-row :gutter="12" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header"><span>校验记录</span></div>
          <div class="kpi-value">{{ validationSummary.total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-header"><span>可评估</span></div>
          <div class="kpi-value text-blue">{{ validationSummary.evaluable }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card kpi-ok">
          <div class="kpi-header"><span>正常 (≤5%内)</span></div>
          <div class="kpi-value text-green">{{ validationSummary.normal }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card kpi-warn">
          <div class="kpi-header"><span>关注 (>5%偏差)</span></div>
          <div class="kpi-value text-amber">{{ validationSummary.warning }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card kpi-danger">
          <div class="kpi-header"><span>重点偏离</span></div>
          <div class="kpi-value text-red">{{ validationSummary.critical }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 走势图 -->
    <section class="sop-panel report-card">
      <div class="report-card-header">
        <div>
          <h3 class="card-title">S&OP 需求走势：历史出库/激活与未来 6 个月 AI 预测、提报走势图</h3>
          <p class="card-subtitle">
            SPU: {{ spuCode || "—" }} · 区域: {{ region || "全部区域" }} · 数据来源: 企业数据仓库 ·
            数据时点: {{ asOfDate }} · 依据《S&OP 报表规则说明》构建
          </p>
        </div>
        <el-button text type="primary" size="small">规则版本已内嵌至规则分区</el-button>
      </div>
      <SopTrendChart :data="trendData" />
    </section>

    <!-- 预测校验明细表 -->
    <section class="sop-panel report-card">
      <div class="report-card-header">
        <div>
          <h3 class="card-title">预测校验结果与证据</h3>
          <p class="card-subtitle">
            判定规则：偏差率 > 5% 标记黄色并触发重点关注；偏差率 > 15% 标记重点偏离。证据来源：AI
            基线模型、库存与周转、客户订单、渠道能力、代际切换等。
          </p>
        </div>
        <span class="rule-version">规则版本已内嵌至规则分区</span>
      </div>
      <ForecastValidationTable :checks="report?.forecast_checks ?? []" />
    </section>

    <section v-if="report" class="sop-panel report-card">
      <div class="report-card-header">
        <div>
          <h3 class="card-title">分渠道提报预测对比矩阵</h3>
          <p class="card-subtitle">
            按未来六个月对比渠道提报与 AI 基线，黄色单元格表示偏差绝对值超过 5%。
          </p>
        </div>
      </div>
      <ChannelForecastMatrix :matrix="channelMatrix" compact />
    </section>

    <div v-if="report" class="sop-insight-grid">
      <section class="sop-panel sop-insight-panel">
        <div class="sop-section-heading">
          <div>
            <span class="sop-heading-icon">✓</span>
            <h3>决策摘要</h3>
          </div>
        </div>
        <div class="sop-rule-list">
          <p><strong>归因分析</strong>{{ decisionSummary.attribution }}</p>
          <p><strong>供应侧</strong>{{ decisionSummary.supply }}</p>
          <p><strong>市场侧</strong>{{ decisionSummary.marketing }}</p>
        </div>
      </section>
      <section class="sop-panel sop-insight-panel">
        <div class="sop-section-heading">
          <div>
            <span class="sop-heading-icon muted">↗</span>
            <h3>数据血缘</h3>
          </div>
        </div>
        <div v-if="report.provenance?.length" class="sop-lineage-list">
          <p v-for="item in report.provenance" :key="`${item.domain}-${item.batch_id}`">
            <strong>{{ item.domain }}</strong
            ><span>{{ item.source_system }} / {{ item.source_table }}</span
            ><small>{{ item.snapshot_at || item.batch_id }}</small>
          </p>
        </div>
        <el-empty v-else :image-size="52" description="当前报告未返回数据血缘记录" />
      </section>
    </div>

    <el-empty v-if="!report && !loading" description="选择 SPU 后加载校验数据" />
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { computed, onMounted, ref } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";
import { SopReportAPI } from "@/api/module_sop/report";
import type { SopFirstPhaseReport, SopSpuInfo } from "@/api/module_sop/types";
import { buildForecastValidationSummary, formatSpuLabel } from "../shared/presentation";
import { buildDecisionSummary } from "../shared/report-metrics";
import { buildChannelForecastMatrix, buildTrendChartDataset } from "../shared/report-data";
import ChannelForecastMatrix from "../shared/ChannelForecastMatrix.vue";
import ForecastValidationTable from "../shared/ForecastValidationTable.vue";
import SopTrendChart from "../shared/SopTrendChart.vue";

defineOptions({ name: "SopAnalysis" });

const spuCode = ref("");
const spuOptions = ref<SopSpuInfo[]>([]);
const spuLoading = ref(false);
const region = ref("");
const channel = ref("");
const regions = ref<string[]>([]);
const channels = ref<string[]>([]);
const period = ref(new Date().toISOString().slice(0, 7));
const report = ref<SopFirstPhaseReport | null>(null);
const loading = ref(false);

const trendData = computed(() => buildTrendChartDataset(report.value));
const channelMatrix = computed(() => buildChannelForecastMatrix(report.value));
const validationSummary = computed(() =>
  buildForecastValidationSummary(report.value?.forecast_checks ?? [])
);
const decisionSummary = computed(() => buildDecisionSummary(report.value));
const asOfDate = computed(() => {
  if (!period.value) return "—";
  const [y = 0, m = 0] = period.value.split("-").map(Number);
  return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
});

async function searchSpus(query: string) {
  if (!query) return;
  spuLoading.value = true;
  try {
    const res = await SopDataAPI.getSpuList({ search: query, limit: 20 });
    spuOptions.value = res.data?.data?.items ?? [];
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
  channel.value = "";
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
      channel: channel.value,
    });
    report.value = res.data?.data ?? null;
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
  height: 92px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.kpi-header {
  font-size: 13px;
  color: #909399;
  font-weight: 500;
}
.kpi-value {
  font-size: 30px;
  font-weight: 800;
  color: #141b2d;
  line-height: 1.15;
  letter-spacing: -0.5px;
  margin-top: 4px;
}
.kpi-ok .kpi-header {
  color: #52c41a;
}
.kpi-warn .kpi-header {
  color: #faad14;
}
.kpi-danger .kpi-header {
  color: #ff4d4f;
}
.text-blue {
  color: #2563eb;
}
.text-green {
  color: #52c41a;
}
.text-amber {
  color: #faad14;
}
.text-red {
  color: #ff4d4f;
}

.report-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-title {
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
.rule-version {
  font-size: 12px;
  color: #909399;
}

@media (max-width: 1050px) {
  :deep(.el-col-6),
  :deep(.el-col-4) {
    width: 50%;
    max-width: 50%;
    flex: 0 0 50%;
    margin-bottom: 12px;
  }
}

@media (max-width: 680px) {
  :deep(.el-col-6),
  :deep(.el-col-4) {
    width: 100%;
    max-width: 100%;
    flex-basis: 100%;
  }
}
</style>
