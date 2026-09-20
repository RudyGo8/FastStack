<template>
  <div class="welcome-banner mb-5">
    <div
      class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between px-8 py-6 text-white"
    >
      <div>
        <h2 class="m-0 mb-2 text-2xl font-semibold">{{ greeting }}，{{ displayName }}</h2>
        <div class="flex items-center flex-wrap gap-3">
          <ElTag :type="roleTagType" size="small" effect="plain">{{ roleText }}</ElTag>
          <span v-if="basicInfo?.dept_name" class="text-sm opacity-90">{{
            basicInfo.dept_name
          }}</span>
        </div>
      </div>
      <div class="flex flex-wrap gap-6 md:justify-end">
        <div class="flex items-center gap-2">
          <FaSvgIcon icon="ri:time-line" class="text-lg" />
          <span class="text-xl font-semibold font-mono">{{ currentTime }}</span>
        </div>
        <div class="flex items-center gap-2">
          <FaSvgIcon icon="ri:calendar-line" class="text-lg" />
          <span>{{ currentDate }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useUserStore } from "@stores";

const { t } = useI18n();
const userStore = useUserStore();
const basicInfo = computed(() => userStore.basicInfo);

const displayName = computed(() => basicInfo.value?.name || basicInfo.value?.username || "-");

const roleText = computed(() => {
  if (basicInfo.value?.is_superuser) return t("home.superAdmin");
  return basicInfo.value?.role_names?.[0] || basicInfo.value?.username || "-";
});

const roleTagType = computed(() => (basicInfo.value?.is_superuser ? "danger" : "primary"));

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 6) return t("home.greetings.lateNight");
  if (hour < 9) return t("home.greetings.morning");
  if (hour < 12) return t("home.greetings.forenoon");
  if (hour < 14) return t("home.greetings.noon");
  if (hour < 18) return t("home.greetings.afternoon");
  if (hour < 22) return t("home.greetings.evening");
  return t("home.greetings.night");
});

const currentTime = ref("");
const currentDate = ref("");
let timer: number | null = null;

const updateTime = () => {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  currentTime.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  const week = t(
    `home.weekdays.${["sun", "mon", "tue", "wed", "thu", "fri", "sat"][now.getDay()]}`
  );
  currentDate.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${week}`;
};

const startTimer = () => {
  if (timer === null) {
    updateTime();
    timer = window.setInterval(updateTime, 1000);
  }
};

const stopTimer = () => {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
};

onMounted(startTimer);
onUnmounted(stopTimer);
// 页面被 KeepAlive 缓存时暂停/恢复时钟
onActivated(startTimer);
onDeactivated(stopTimer);
</script>

<style scoped>
.welcome-banner {
  background: linear-gradient(
    135deg,
    var(--theme-color) 0%,
    color-mix(in srgb, var(--theme-color) 40%, #6f7bff) 100%
  );
  border-radius: 16px;
  overflow: hidden;
}
</style>
