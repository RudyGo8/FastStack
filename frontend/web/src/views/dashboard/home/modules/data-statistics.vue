<template>
  <ElRow :gutter="20">
    <ElCol v-for="item in cards" :key="item.key" :xs="24" :sm="12" :lg="6" class="mb-5">
      <div
        class="fa-card h-36 px-6 py-5 transition-shadow"
        :class="{ 'cursor-pointer hover:shadow-md': item.clickable }"
        @click="item.clickable ? go(item.to) : undefined"
      >
        <div class="flex h-full items-start justify-between">
          <div class="flex flex-col justify-between h-full">
            <div class="text-3xl font-bold leading-none">
              <FaCountTo :target="item.value" :duration="1200" />
            </div>
            <div>
              <div class="text-sm font-medium text-g-600">{{ item.label }}</div>
              <div class="mt-1 text-xs text-g-500">{{ item.meta }}</div>
            </div>
          </div>
          <div class="size-12 rounded-xl flex items-center justify-center" :class="item.iconBg">
            <FaSvgIcon :icon="item.icon" class="text-2xl" :class="item.iconColor" />
          </div>
        </div>
      </div>
    </ElCol>
  </ElRow>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import DashboardAPI, { type DashboardStatistics } from "@/api/module_monitor/dashboard";

const { t } = useI18n();
const router = useRouter();

const statistics = ref<DashboardStatistics>({
  notice_published: 0,
  notice_total: 0,
  today_logins: 0,
  week_logins: 0,
  today_operations: 0,
  week_operations: 0,
});

const cards = computed(() => [
  {
    key: "notice_published",
    value: statistics.value.notice_published,
    label: t("home.publishedNotices"),
    meta: `${t("home.allNotices")} ${statistics.value.notice_total}`,
    icon: "ri:notification-3-line",
    iconBg: "bg-danger/10",
    iconColor: "text-danger",
    to: "/system/notice",
    clickable: false,
  },
  {
    key: "notice_total",
    value: statistics.value.notice_total,
    label: t("home.allNotices"),
    meta: t("home.goToNotice"),
    icon: "ri:megaphone-line",
    iconBg: "bg-warning/10",
    iconColor: "text-warning",
    to: "/system/notice",
    clickable: false,
  },
  {
    key: "today_logins",
    value: statistics.value.today_logins,
    label: t("home.todayLogins"),
    meta: `${t("home.last7Days")} ${statistics.value.week_logins}`,
    icon: "ri:login-box-line",
    iconBg: "bg-theme/10",
    iconColor: "text-theme",
    to: "/system/log",
    clickable: false,
  },
  {
    key: "today_operations",
    value: statistics.value.today_operations,
    label: t("home.todayOperations"),
    meta: `${t("home.last7Days")} ${statistics.value.week_operations}`,
    icon: "ri:cursor-line",
    iconBg: "bg-success/10",
    iconColor: "text-success",
    to: "/system/log",
    clickable: false,
  },
]);

const go = (path: string) => {
  router.push(path).catch(() => ElMessage.warning(t("home.routeNotFound", { href: path })));
};

onMounted(async () => {
  try {
    const res = await DashboardAPI.getStatistics();
    if (res.data?.data) statistics.value = res.data.data;
  } catch {
    /* 统计加载失败不打断首页 */
  }
});
</script>
