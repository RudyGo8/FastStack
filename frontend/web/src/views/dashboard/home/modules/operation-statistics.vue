<template>
  <div class="fa-card p-5">
    <div class="mb-4">
      <h3 class="text-base font-medium m-0">{{ t("home.operationStatistics") }}</h3>
      <p class="text-xs text-g-600 mt-1 mb-0">{{ t("home.operationStatisticsDesc") }}</p>
    </div>

    <ElRow :gutter="20">
      <ElCol :xs="24" :md="8" class="mb-4 md:mb-0">
        <div class="text-sm text-g-600 mb-2">{{ t("home.typeDistribution") }}</div>
        <FaRingChart
          :data="operationStats.type_distribution"
          height="260px"
          :show-legend="true"
          legend-position="bottom"
        />
      </ElCol>
      <ElCol :xs="24" :md="8" class="mb-4 md:mb-0">
        <div class="text-sm text-g-600 mb-2">{{ t("home.moduleTop") }}</div>
        <FaRingChart
          :data="operationStats.module_distribution"
          height="260px"
          :show-legend="true"
          legend-position="bottom"
        />
      </ElCol>
      <ElCol :xs="24" :md="8">
        <div class="text-sm text-g-600 mb-2">{{ t("home.operationTrend") }}</div>
        <FaLineChart
          :data="operationStats.daily_trend"
          :x-axis-data="operationStats.dates"
          height="260px"
          :show-area-color="true"
        />
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import DashboardAPI, { type OperationStatistics } from "@/api/module_monitor/dashboard";

const { t } = useI18n();

const operationStats = ref<OperationStatistics>({
  dates: [],
  type_distribution: [],
  daily_trend: [],
  module_distribution: [],
});

onMounted(async () => {
  try {
    const res = await DashboardAPI.getOperationStatistics();
    if (res.data?.data) operationStats.value = res.data.data;
  } catch {
    /* 统计加载失败不打断首页 */
  }
});
</script>
