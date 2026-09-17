<template>
  <el-table :data="points" border size="small" max-height="420">
    <el-table-column prop="period" label="月份" width="100" align="center" fixed />
    <el-table-column label="出库数量" width="120" align="right">
      <template #default="{ row }">{{ fmt(row.outbound_qty) }}</template>
    </el-table-column>
    <el-table-column label="激活数量" width="110" align="right">
      <template #default="{ row }">{{ fmt(row.activation_qty) }}</template>
    </el-table-column>
    <el-table-column label="提报预测出库数量" width="140" align="right">
      <template #default="{ row }">
        <span :class="{ 'diff-submit': row.submit_forecast && row.submit_forecast > 0 }">{{
          row.submit_forecast ?? "—"
        }}</span>
      </template>
    </el-table-column>
    <el-table-column label="发生事件" min-width="220" show-overflow-tooltip>
      <template #default="{ row }">{{ row.event || "—" }}</template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { SopTrendPoint } from "@/api/module_sop/types";

defineProps<{ points: SopTrendPoint[] }>();

function fmt(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("zh-CN");
}
</script>

<style scoped>
.diff-submit {
  color: #2563eb;
  font-weight: 600;
}
</style>
