<template>
  <div class="flex flex-col relative last:mb-0">
    <ElRow :gutter="20">
      <ElCol v-if="hasDashboardPerm" :xs="24" :md="18" class="mb-5">
        <CardList />
      </ElCol>
      <ElCol :xs="24" :md="6" class="flex flex-col gap-5">
        <QuickLinks class="mb-5" />
        <FaDataListCard
          class="mb-5"
          :maxCount="4"
          :list="healthList"
          :title="t('home.systemHealth')"
          :subtitle="t('home.realtime')"
        />
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "Home", inheritAttrs: false });

import { ref, computed, onMounted, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
import { checkPerm } from "@/utils/checkPerm";
import DashboardAPI, { type HealthItem } from "@/api/module_monitor/dashboard";
import CardList from "./modules/card-list.vue";
import QuickLinks from "./modules/quick-links.vue";

const { t } = useI18n();
const hasDashboardPerm = computed(() => checkPerm("module_monitor:dashboard:query"));
const healthList = ref<HealthItem[]>([]);

let unsubscribeHealth: (() => void) | null = null;

onMounted(() => {
  unsubscribeHealth = DashboardAPI.subscribeHealthStream((items) => {
    healthList.value = items;
  });
});

onUnmounted(() => {
  unsubscribeHealth?.();
  unsubscribeHealth = null;
});

</script>
