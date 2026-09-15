<template>
  <div class="fa-card p-5 mb-5">
    <div class="mb-4">
      <h3 class="text-base font-medium m-0">{{ t("home.loginStatistics") }}</h3>
      <p class="text-xs text-g-600 mt-1 mb-0">{{ t("home.loginStatisticsDesc") }}</p>
    </div>

    <ElRow :gutter="20">
      <ElCol :xs="24" :md="8" class="mb-4 md:mb-0">
        <div class="text-sm text-g-600 mb-2">{{ t("home.osDistribution") }}</div>
        <FaRingChart
          :data="loginStats.os_distribution"
          height="260px"
          :show-legend="true"
          legend-position="bottom"
        />
      </ElCol>
      <ElCol :xs="24" :md="8" class="mb-4 md:mb-0">
        <div class="text-sm text-g-600 mb-2">{{ t("home.browserDistribution") }}</div>
        <FaRingChart
          :data="loginStats.browser_distribution"
          height="260px"
          :show-legend="true"
          legend-position="bottom"
        />
      </ElCol>
      <ElCol :xs="24" :md="8">
        <div class="text-sm text-g-600 mb-2">{{ t("home.locationTop") }}</div>
        <FaHBarChart :data="locationValues" :x-axis-data="locationNames" height="260px" />
      </ElCol>
    </ElRow>

    <div class="mt-5 pt-5" style="border-top: 1px solid var(--el-border-color-lighter)">
      <div class="text-sm text-g-600 mb-2">{{ t("home.loginTrend") }}</div>
      <FaLineChart
        :data="trendSeries"
        :x-axis-data="trend.dates"
        height="300px"
        :show-legend="true"
        legend-position="bottom"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import DashboardAPI, {
  type LoginStatistics,
  type LoginTrend,
} from "@/api/module_monitor/dashboard";

const { t } = useI18n();

const loginStats = ref<LoginStatistics>({
  os_distribution: [],
  browser_distribution: [],
  location_distribution: [],
});
const trend = ref<LoginTrend>({ dates: [], login_counts: [], location_series: [] });

const locationNames = computed(() =>
  loginStats.value.location_distribution.map((item) => item.name)
);
const locationValues = computed(() =>
  loginStats.value.location_distribution.map((item) => item.value)
);

const trendSeries = computed(() => [
  { name: t("home.totalLogins"), data: trend.value.login_counts, showAreaColor: true },
  ...trend.value.location_series.map((series) => ({ name: series.name, data: series.data })),
]);

onMounted(async () => {
  try {
    const [statsRes, trendRes] = await Promise.all([
      DashboardAPI.getLoginStatistics(),
      DashboardAPI.getLoginTrend(),
    ]);
    if (statsRes.data?.data) loginStats.value = statsRes.data.data;
    if (trendRes.data?.data) trend.value = trendRes.data.data;
  } catch {
    /* 统计加载失败不打断首页 */
  }
});
</script>
