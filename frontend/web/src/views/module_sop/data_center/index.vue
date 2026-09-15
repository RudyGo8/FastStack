<template>
  <div class="fa-full-height sop-workspace sop-page data-center-page">
    <div class="sop-page-heading">
      <div>
        <span class="sop-heading-icon">▦</span>
        <div>
          <h2>数据中心</h2>
          <p>查看数据同步状态、SPU 主数据与当前预测校验口径</p>
        </div>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新全部</el-button>
    </div>
    <el-tabs v-model="activeTab" type="border-card" class="sop-data-tabs">
      <el-tab-pane label="数据源同步" name="sources">
        <div class="mb-3 flex items-center gap-3">
          <el-tag :type="sourceConnectionConfigured ? 'success' : 'danger'">
            {{ sourceConnectionConfigured ? "企业数仓连接正常" : "企业数仓尚未配置" }}
          </el-tag>
          <el-tag type="primary"
            >一期核心：{{ readyCoreCount }}/{{ coreSourceCount }} 已同步</el-tag
          >
          <el-tag :type="openIssues ? 'warning' : 'success'">未决质量问题：{{ openIssues }}</el-tag
          ><el-button type="primary" :loading="syncing" @click="handleSync"
            >从企业数仓同步数据</el-button
          >
        </div>
        <el-table :data="sources" border stripe v-loading="loading">
          <el-table-column prop="label" label="数据域" width="140" /><el-table-column
            label="物理来源视图"
            min-width="180"
            ><template #default="{ row }">{{
              row.source_objects?.join("、") || "—"
            }}</template></el-table-column
          >
          <el-table-column label="接入阶段" width="100">
            <template #default="{ row }">{{ phaseLabel(row.phase_scope) }}</template>
          </el-table-column>
          <el-table-column label="同步状态" width="130"
            ><template #default="{ row }"
              ><el-tag :type="getSourceSyncDisplay(row.ingestion_status, row.phase_scope).type">{{
                getSourceSyncDisplay(row.ingestion_status, row.phase_scope).label
              }}</el-tag></template
            ></el-table-column
          >
          <el-table-column
            prop="latest_snapshot_at"
            label="最新同步时点"
            width="180"
          /><el-table-column
            prop="max_business_date"
            label="最新业务日期"
            width="130"
          /><el-table-column prop="record_count" label="记录数" width="100" /><el-table-column
            prop="note"
            label="说明"
            min-width="220"
          />
          <template #empty><el-empty description="尚未接入数据源" /></template>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="数据导入" name="imports">
        <el-alert
          type="info"
          :closable="false"
          title="Excel 首行为字段名；导入结果会保留接受、拒绝和质量问题编号。"
          class="mb-4"
        />
        <div class="flex flex-wrap gap-3">
          <el-upload
            v-for="item in importActions"
            :key="item.domain"
            :show-file-list="false"
            :http-request="(option: any) => handleImport(option, item.domain)"
            accept=".xlsx,.xls"
            ><el-button :loading="importing === item.domain">{{ item.label }}</el-button></el-upload
          >
        </div>
        <el-table v-if="importResults.length" :data="importResults" border class="mt-4"
          ><el-table-column prop="time" label="时间" width="180" /><el-table-column
            prop="domain"
            label="数据域"
            width="120" /><el-table-column prop="status" label="状态" width="100" /><el-table-column
            label="接受/拒绝"
            width="120"
            ><template #default="{ row }"
              >{{ row.accepted }} / {{ row.rejected }}</template
            ></el-table-column
          ><el-table-column label="质量问题"
            ><template #default="{ row }">{{
              row.quality_issue_ids?.join("、") || "—"
            }}</template></el-table-column
          ><el-table-column prop="batch_id" label="批次" min-width="180"
        /></el-table>
      </el-tab-pane>
      <el-tab-pane label="SPU 主数据" name="spus">
        <el-card shadow="never" header="SPU 品类主数据字典"
          ><el-table :data="spus" border stripe
            ><el-table-column prop="spu_code" label="SPU 编码" /><el-table-column
              prop="spu_name"
              label="SPU 名称" /><el-table-column
              prop="product_line"
              label="所属产品线" /><el-table-column label="品牌 / 品类"
              ><template #default="{ row }"
                >{{ row.brand || "—" }} / {{ row.category || "—" }}</template
              ></el-table-column
            ><el-table-column prop="lifecycle_stage" label="生命周期" /><template #empty
              ><el-empty description="暂无 SPU 主数据" /></template></el-table
        ></el-card>
      </el-tab-pane>
      <el-tab-pane label="校验规则" name="rules">
        <el-card shadow="never" header="预测校验默认口径（草案）"
          ><el-descriptions :column="3" border
            ><el-descriptions-item label="偏差 ≤ 5%"
              ><el-tag type="success">正常</el-tag></el-descriptions-item
            ><el-descriptions-item label="5% < 偏差 ≤ 15%"
              ><el-tag type="warning">关注</el-tag></el-descriptions-item
            ><el-descriptions-item label="偏差 > 15%"
              ><el-tag type="danger">重点偏离</el-tag></el-descriptions-item
            ><el-descriptions-item label="评估原则" :span="3"
              >所有等级以服务端确定性规则结果为准；基线缺失时标记为暂不可评估，不用零值代替。</el-descriptions-item
            ></el-descriptions
          ></el-card
        >
      </el-tab-pane>
      <el-tab-pane label="会前数据快照" name="snapshots">
        <el-alert
          title="S&OP 会前数据快照固化策略（T-1 业务基线）"
          type="info"
          :closable="false"
          description="系统每日夜间固化活跃 SPU 截至前一天的出库、激活、预测事实与规则校验结果，确保会议使用统一且不可变的业务基线。"
          class="mb-4"
        />
        <div class="mb-3">
          <el-button type="primary" :loading="generating" @click="generateSnapshots"
            >立即生成快照</el-button
          >
        </div>
        <el-card shadow="never" header="会前不可变快照历史记录"
          ><el-table :data="snapshots" border stripe
            ><el-table-column prop="id" label="快照 ID" /><el-table-column
              prop="spu_code"
              label="SPU 编码" /><el-table-column
              prop="report_version"
              label="版本" /><el-table-column
              prop="as_of_date"
              label="业务截止日" /><el-table-column
              prop="completeness_status"
              label="齐套完整性" /><el-table-column
              prop="record_count"
              label="记录数" /><el-table-column
              prop="generated_at"
              label="生成时间"
              min-width="170" /><template #empty
              ><el-empty description="暂无会前数据快照记录" /></template></el-table
        ></el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { SopDataAPI } from "@/api/module_sop/data";
import { SopReportAPI } from "@/api/module_sop/report";
import type {
  SopImportResponse,
  SopReportSnapshotSummary,
  SopSourceStatus,
  SopSpuInfo,
} from "@/api/module_sop/types";
import { getSourceSyncDisplay } from "../shared/report-metrics";

defineOptions({ name: "SopDataCenter" });
type ImportDomain = "spus" | "sales" | "activations" | "forecasts" | "events";
type ImportLog = SopImportResponse & { time: string };
const activeTab = ref("sources");
const sources = ref<SopSourceStatus[]>([]);
const sourceConnectionConfigured = ref(false);
const openIssues = ref(0);
const spus = ref<SopSpuInfo[]>([]);
const snapshots = ref<SopReportSnapshotSummary[]>([]);
const loading = ref(false);
const syncing = ref(false);
const generating = ref(false);
const importing = ref<ImportDomain | "">("");
const importResults = ref<ImportLog[]>([]);
const importActions: { domain: ImportDomain; label: string }[] = [
  { domain: "spus", label: "导入 SPU 主数据" },
  { domain: "sales", label: "导入销售事实" },
  { domain: "activations", label: "导入激活事实" },
  { domain: "forecasts", label: "导入预测数据" },
  { domain: "events", label: "导入发生事件" },
];
const coreSources = computed(() =>
  sources.value.filter((source) => source.phase_scope === "phase_one_core")
);
const coreSourceCount = computed(() => coreSources.value.length);
const readyCoreCount = computed(
  () => coreSources.value.filter((source) => source.ingestion_status === "completed").length
);

function phaseLabel(scope: string): string {
  if (scope === "phase_one_core") return "一期核心";
  if (scope === "phase_one_extension") return "扩展域";
  if (scope === "connection_only") return "二期预留";
  return "待确认";
}

async function loadAll(): Promise<void> {
  loading.value = true;
  try {
    const [status, spuResult, snapshotResult] = await Promise.all([
      SopDataAPI.getDataStatus(),
      SopDataAPI.getSpuList({ limit: 100 }),
      SopReportAPI.getSnapshotList({ limit: 100 }),
    ]);
    sources.value = status.data?.data?.sources ?? [];
    sourceConnectionConfigured.value = Boolean(status.data?.data?.source_connection_configured);
    openIssues.value = status.data?.data?.open_quality_issues ?? 0;
    spus.value = spuResult.data?.data?.items ?? [];
    snapshots.value = snapshotResult.data?.data ?? [];
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "数据中心加载失败");
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
    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
      defval: null,
      raw: false,
    });
    if (!rows.length) throw new Error("表格无数据行");
    const meta = {
      source_system: "manual_import",
      source_table: option.file.name,
      batch_id: `IMP_${Date.now()}`,
      snapshot_at: new Date().toISOString(),
    };
    const api = {
      spus: SopDataAPI.importSpus,
      sales: SopDataAPI.importSales,
      activations: SopDataAPI.importActivations,
      forecasts: SopDataAPI.importForecasts,
      events: SopDataAPI.importEvents,
    }[domain];
    const data = (await api({ meta, rows })).data?.data;
    if (data)
      importResults.value.unshift({
        ...data,
        time: new Date().toLocaleString("zh-CN", { hour12: false }),
      });
    ElMessage.success(`导入完成：接受 ${data?.accepted ?? 0} 条，拒绝 ${data?.rejected ?? 0} 条`);
    await loadAll();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "导入失败");
  } finally {
    importing.value = "";
  }
}
async function handleSync(): Promise<void> {
  syncing.value = true;
  try {
    const result = await SopDataAPI.syncWarehouse();
    ElMessage.success(result.data?.data?.message || "数仓同步成功");
    await loadAll();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "数仓同步失败");
  } finally {
    syncing.value = false;
  }
}
async function generateSnapshots(): Promise<void> {
  generating.value = true;
  try {
    await SopReportAPI.generateSnapshots();
    ElMessage.success("会前快照生成完成");
    await loadAll();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "快照生成失败");
  } finally {
    generating.value = false;
  }
}
onMounted(loadAll);
</script>

<style scoped>
.sop-page-heading,
.sop-page-heading > div {
  display: flex;
  align-items: center;
}
.sop-page-heading {
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fff;
}
.sop-page-heading > div {
  gap: 9px;
}
.sop-page-heading h2 {
  margin: 0;
  color: #141b2d;
  font-size: 16px;
}
.sop-page-heading p {
  margin: 2px 0 0;
  color: #94a3b8;
  font-size: 11.5px;
}
.sop-data-tabs {
  flex: 1;
  min-height: 0;
  border-color: #e6ebf2;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: none;
}
:deep(.el-tabs__header) {
  background: #f8fafc;
}
:deep(.el-tabs__item) {
  height: 38px;
  color: #64748b;
  font-size: 12px;
}
:deep(.el-tabs__item.is-active) {
  color: #2563eb;
  background: #fff;
}
</style>
