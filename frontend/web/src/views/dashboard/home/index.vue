<template>
  <div class="flex flex-col">
    <WelcomeBanner />
    <DataStatistics />
    <LoginStatistics />
    <OperationStatistics />
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "Home", inheritAttrs: false });

import WelcomeBanner from "./modules/welcome-banner.vue";
import DataStatistics from "./modules/data-statistics.vue";
import LoginStatistics from "./modules/login-statistics.vue";
import OperationStatistics from "./modules/operation-statistics.vue";
</script>
