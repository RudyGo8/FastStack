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
            <td v-for="month in matrix.months" :key="month">
              {{ formatNumber(matrix.submitMatrix[channel]?.[matrix.months.indexOf(month)]) }}
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
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { SopChannelMatrix } from "@/api/module_sop/types";

const props = defineProps<{
  matrix: SopChannelMatrix;
  compact?: boolean;
}>();

const visibleChannels = computed(() => [...props.matrix.channels, "合计"]);

function formatNumber(value: number | undefined): string {
  if (value === undefined || value === null) return "—";
  return value.toLocaleString("zh-CN");
}
</script>

<style scoped>
.channel-matrix {
  width: 100%;
}
.matrix-table-wrap {
  overflow-x: auto;
}
.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.matrix-table th,
.matrix-table td {
  padding: 8px 12px;
  text-align: right;
  border-bottom: 1px solid #e5e7eb;
}
.matrix-table th {
  background: var(--sop-subtle);
  font-weight: 600;
  color: #374151;
  text-align: center;
}
.matrix-table th:first-child,
.matrix-table td:first-child {
  text-align: left;
  font-weight: 500;
  position: sticky;
  left: 0;
  background: var(--sop-surface);
  z-index: 1;
}
.matrix-table tbody tr:hover {
  background: var(--sop-subtle);
}
.matrix-table tbody tr.total {
  background: #eff6ff;
  font-weight: 700;
}
.matrix-table tbody tr.total td:first-child {
  background: #eff6ff;
}
</style>
