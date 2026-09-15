<template>
  <div class="channel-matrix">
    <div class="matrix-table-wrap">
      <table class="matrix-table">
        <thead>
          <tr>
            <th>销售渠道</th>
            <th v-for="month in matrix.months" :key="month">{{ month }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="channel in visibleChannels"
            :key="channel"
            :class="{ total: channel === '合计' }"
          >
            <th>{{ channel }}</th>
            <td
              v-for="(month, index) in matrix.months"
              :key="month"
              :class="deviationClass(matrix.deviationMatrix[channel]?.[index])"
              :title="annotation(channel, month)"
            >
              <span>{{ formatNumber(matrix.submitMatrix[channel]?.[index]) }}</span>
              <small v-if="!compact && channel !== '合计'"
                >AI {{ formatNumber(matrix.aiBaselineMatrix[channel]?.[index]) }}</small
              >
              <i v-if="annotation(channel, month)" aria-label="有差异批注">●</i>
            </td>
          </tr>
        </tbody>
      </table>
      <el-empty
        v-if="!matrix.months.length"
        :image-size="52"
        description="当前筛选范围暂无渠道预测数据"
      />
    </div>

    <div v-if="!compact && matrix.diffList.length" class="matrix-differences">
      <div class="matrix-difference-title">
        <strong>差异清单</strong><span>提报预测与 AI 基线偏差绝对值 &gt; 5%</span>
      </div>
      <el-table :data="matrix.diffList" border size="small" max-height="360">
        <el-table-column prop="channel" label="渠道" width="120" />
        <el-table-column prop="month" label="月份" width="95" align="center" />
        <el-table-column prop="aiQty" label="AI预测" width="95" align="right" />
        <el-table-column prop="submitQty" label="提报预测" width="100" align="right" />
        <el-table-column label="差异率" width="90" align="right">
          <template #default="{ row }"
            ><strong :class="row.deviationRatio > 0 ? 'diff-up' : 'diff-down'"
              >{{ row.deviationRatio > 0 ? "+" : ""
              }}{{ (row.deviationRatio * 100).toFixed(1) }}%</strong
            ></template
          >
        </el-table-column>
        <el-table-column prop="dimension" label="校验维度" width="130" />
        <el-table-column prop="reason" label="差异原因" min-width="220" show-overflow-tooltip />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { SopChannelDifference, SopChannelMatrix } from "@/api/module_sop/types";

const props = withDefaults(defineProps<{ matrix: SopChannelMatrix; compact?: boolean }>(), {
  compact: false,
});

const visibleChannels = computed(() => {
  const channels = props.matrix.channels.filter(
    (channel) => props.matrix.submitMatrix[channel] !== undefined
  );
  return props.matrix.submitMatrix["合计"] ? [...channels, "合计"] : channels;
});

const annotationMap = computed(() => {
  const map = new Map<string, SopChannelDifference>();
  for (const item of props.matrix.diffList) map.set(`${item.channel}|${item.month}`, item);
  return map;
});

function annotation(channel: string, month: string): string {
  const item = annotationMap.value.get(`${channel}|${month}`);
  if (!item) return "";
  const rate = `${item.deviationRatio > 0 ? "+" : ""}${(item.deviationRatio * 100).toFixed(1)}%`;
  return `偏差 ${rate}｜${item.dimension}：${item.reason}`;
}

function formatNumber(value: number | undefined): string {
  return value === undefined ? "—" : Number(value).toLocaleString("zh-CN");
}

function deviationClass(value: number | undefined): string {
  if (value === undefined) return "";
  const absolute = Math.abs(value);
  if (absolute > 0.15) return "variance-cell variance-critical";
  if (absolute > 0.05) return "variance-cell";
  return "";
}
</script>

<style scoped>
.matrix-table-wrap {
  overflow-x: auto;
  border: 1px solid #e6ebf2;
  border-radius: 7px;
  background: #fff;
}
.matrix-table {
  width: 100%;
  border-collapse: collapse;
  color: #334155;
  font-size: 11.5px;
  table-layout: fixed;
}
.matrix-table th,
.matrix-table td {
  min-width: 112px;
  padding: 7px 10px;
  border-right: 1px solid #eef2f6;
  border-bottom: 1px solid #eef2f6;
  text-align: right;
  white-space: nowrap;
}
.matrix-table thead th {
  color: #475569;
  background: #f1f5f9;
  font-weight: 650;
  text-align: center;
}
.matrix-table thead th:first-child,
.matrix-table tbody th {
  width: 150px;
  min-width: 150px;
  text-align: left;
}
.matrix-table tbody th {
  color: #334155;
  background: #fcfdfe;
  font-weight: 600;
}
.matrix-table tr:last-child th,
.matrix-table tr:last-child td {
  border-bottom: 0;
}
.matrix-table th:last-child,
.matrix-table td:last-child {
  border-right: 0;
}
.matrix-table td {
  position: relative;
}
.matrix-table td span {
  display: block;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
}
.matrix-table td small {
  display: block;
  margin-top: 1px;
  color: #94a3b8;
  font-size: 9.5px;
}
.matrix-table td i {
  position: absolute;
  top: 4px;
  right: 5px;
  color: #d97706;
  font-size: 6px;
  font-style: normal;
}
.matrix-table .variance-cell {
  background: #fef08a;
  cursor: help;
}
.matrix-table .variance-critical {
  background: #fde68a;
  box-shadow: inset 3px 0 #f59e0b;
}
.matrix-table .total th,
.matrix-table .total td {
  border-top: 2px solid #cbd5e1;
  background: #f8fafc;
  font-weight: 700;
}
.matrix-differences {
  margin-top: 14px;
}
.matrix-difference-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 7px;
  font-size: 11.5px;
}
.matrix-difference-title strong {
  color: #1e293b;
}
.matrix-difference-title span {
  color: #94a3b8;
}
.diff-up {
  color: #dc2626;
}
.diff-down {
  color: #4f46e5;
}
@media (max-width: 720px) {
  .matrix-table {
    table-layout: auto;
  }
}
</style>
