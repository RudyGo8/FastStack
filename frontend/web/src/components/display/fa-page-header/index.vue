<template>
  <ElPageHeader v-bind="$attrs" :icon="iconComponent" :content="content" @back="handleBack">
    <template #default>
      <slot />
    </template>
    <template #extra>
      <slot name="extra" />
    </template>
    <template #breadcrumb>
      <slot name="breadcrumb" />
    </template>
  </ElPageHeader>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ArrowLeft } from "@element-plus/icons-vue";
import type { Component } from "vue";

defineOptions({ name: "FaPageHeader" });

interface Props {
  /** 返回图标（ElPageHeader 的 icon 属性） */
  icon?: string;
  /** 标题内容（ElPageHeader 的 content 属性） */
  content?: string;
  /** 返回回调 */
  onBack?: () => void;
}

const props = withDefaults(defineProps<Props>(), {
  icon: "ArrowLeft",
  content: "",
  onBack: undefined,
});

const iconMap: Record<string, Component> = {
  ArrowLeft,
};

const iconComponent = computed(() => {
  if (!props.icon) return undefined;
  return iconMap[props.icon] ?? props.icon;
});

function handleBack() {
  props.onBack?.();
}
</script>
