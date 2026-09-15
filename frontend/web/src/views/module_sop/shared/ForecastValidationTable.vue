<template>
  <el-table :data="rows" border stripe size="small">
    <el-table-column prop="month" label="预测月" width="110" align="center" />
    <el-table-column prop="scope" label="范围" width="160" show-overflow-tooltip />
    <el-table-column prop="forecastQty" label="预测量" width="100" align="right" />
    <el-table-column prop="baselineQty" label="基线量" width="100" align="right" />
    <el-table-column label="偏差" width="100" align="right">
      <template #default="{ row }">{{ row.deviationRatio != null ? (row.deviationRatio * 100).toFixed(1) + "%" : "—" }}</template>
    </el-table-column>
    <el-table-column label="等级" width="100" align="center">
      <template #default="{ row }">
        <el-tag v-if="!row.evaluable" size="small" type="info">不可评估</el-tag>
        <el-tag v-else-if="row.level === 'low'" size="small" type="success">正常</el-tag>
        <el-tag v-else-if="row.level === 'medium'" size="small" type="warning">关注</el-tag>
        <el-tag v-else-if="row.level === 'high'" size="small" type="danger">重点偏离</el-tag>
        <el-tag v-else size="small">{{ row.level || "—" }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="ruleVersion" label="规则版本" width="130" />
    <el-table-column prop="findingText" label="发现" min-width="240" show-overflow-tooltip />
  </el-table>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { SopForecastCheck } from "@/api/module_sop/types";
import { buildForecastValidationRows } from "./presentation";

const props = defineProps<{ checks: SopForecastCheck[] }>();

const rows = computed(() => buildForecastValidationRows(props.checks));
</script>
