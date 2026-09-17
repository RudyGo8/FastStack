<template>
  <div class="annual-channel-matrix">
    <div v-if="matrix.rows.length" class="annual-table-wrap">
      <table class="annual-channel-table" aria-label="分渠道销售、激活与预测表">
        <colgroup>
          <col class="channel-column" />
          <col class="type-column" />
          <col v-for="(month, index) in matrix.months" :key="index" class="month-column" />
        </colgroup>
        <thead>
          <tr>
            <th rowspan="2" scope="col" class="identity-head">渠道</th>
            <th rowspan="2" scope="col" class="identity-head">类型</th>
            <th
              v-if="matrix.salesMonthCount"
              :colspan="matrix.salesMonthCount"
              scope="colgroup"
              class="group-sales"
            >
              实际出库（按单据日期）
            </th>
            <th :colspan="forecastMonthCount" scope="colgroup" class="group-forecast">
              提报预测（含当月）
            </th>
          </tr>
          <tr>
            <th
              v-for="(month, index) in matrix.months"
              :key="index"
              scope="col"
              :class="index < matrix.salesMonthCount ? 'month-sales' : 'month-forecast'"
            >
              {{ formatMonth(month) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="row in matrix.rows" :key="row.channel">
            <tr class="outbound-row">
              <th rowspan="2" scope="rowgroup" class="channel-name">
                {{ formatChannel(row.channel) }}
              </th>
              <th scope="row" class="type-name">出库/预测</th>
              <td v-for="(value, index) in row.outboundOrForecast" :key="index">
                {{ formatNumber(value) }}
              </td>
            </tr>
            <tr class="activation-row">
              <th scope="row" class="type-name">激活</th>
              <td v-for="(value, index) in row.activations" :key="index">
                {{ formatNumber(value) }}
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <el-empty v-else :image-size="52" description="当前筛选暂无渠道销售、激活或预测数据" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { SopAnnualChannelMatrix } from "@/api/module_sop/types";

const props = defineProps<{ matrix: SopAnnualChannelMatrix }>();

const forecastMonthCount = computed(
  () => props.matrix.months.length - props.matrix.salesMonthCount
);

function formatMonth(month: string): string {
  const [year, value] = month.split("-");
  return `${year}年${Number(value)}月`;
}

function formatChannel(channel: string): string {
  const labels: Record<string, string> = {
    国际渠道销售一部: "海外渠道一部",
    国际渠道销售二部: "海外渠道二部",
  };
  return labels[channel] ?? channel;
}

function formatNumber(value: number | null): string {
  if (value === null || value === undefined) return "";
  return Number(value).toLocaleString("zh-CN", {
    maximumFractionDigits: 2,
    useGrouping: false,
  });
}
</script>

<style scoped>
.annual-channel-matrix {
  width: 100%;
}

.annual-table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #172033;
}

.annual-table-wrap::-webkit-scrollbar {
  height: 10px;
}

.annual-table-wrap::-webkit-scrollbar-track {
  background: #e9edf6;
  border-radius: 5px;
}

.annual-table-wrap::-webkit-scrollbar-thumb {
  background: #94a3b8;
  border-radius: 5px;
  border: 2px solid #e9edf6;
}

.annual-table-wrap::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

.annual-table-wrap {
  scrollbar-width: thin;
  scrollbar-color: #94a3b8 #e9edf6;
}

.annual-channel-table {
  width: 100%;
  min-width: 1180px;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  color: #151922;
  table-layout: fixed;
  border-collapse: collapse;
}

.channel-column {
  width: 112px;
}

.type-column {
  width: 108px;
}

.month-column {
  width: 86px;
}

.annual-channel-table th,
.annual-channel-table td {
  height: 34px;
  padding: 5px 7px;
  text-align: center;
  white-space: nowrap;
  border: 1px solid #172033;
}

.annual-channel-table thead th {
  font-weight: 700;
  color: #fff;
}

.identity-head,
.group-sales,
.month-sales {
  background: #082b68;
}

.group-forecast,
.month-forecast {
  background: #b54708;
}

.group-sales,
.group-forecast {
  height: 36px;
  font-size: 16px;
  letter-spacing: 0.08em;
}

.outbound-row,
.channel-name {
  background: #e9edf6;
}

.activation-row {
  background: #fff;
}

.channel-name,
.type-name {
  font-weight: 500;
}

@media (width <= 720px) {
  .annual-channel-table {
    font-size: 13px;
  }
}
</style>
