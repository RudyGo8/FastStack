<template>
  <ElMenuItemGroup :title="title">
    <slot />
  </ElMenuItemGroup>
</template>

<script setup lang="ts">
defineOptions({ name: "FaMenuItemGroup" });

interface Props {
  /** 分组标题 */
  title: string;
}

defineProps<Props>();
</script>
