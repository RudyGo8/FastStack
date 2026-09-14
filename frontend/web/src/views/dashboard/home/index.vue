<template>
  <div class="flex flex-col relative last:mb-0">
    <ElRow :gutter="20">
      <ElCol :xs="24" :md="18" class="mb-5">
        <CardList />
      </ElCol>
      <ElCol :xs="24" :md="6" class="flex flex-col gap-5">
        <QuickLinks class="mb-5" />
        <FaDataListCard
          class="mb-5"
          :maxCount="4"
          :list="healthList"
          title="系统健康"
          subtitle="实时 · 30s"
          :showMoreButton="true"
          @more="handleMore"
        />
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "Home", inheritAttrs: false });

import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import DashboardAPI, { type HealthItem } from "@/api/module_monitor/dashboard";
import CardList from "./modules/card-list.vue";
import QuickLinks from "./modules/quick-links.vue";

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

function handleMore() {
  ElMessage.info("查看更多");
}
</script>
