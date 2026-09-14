<template>
  <div class="fa-affix">
    <ElAffix :offset="offset" :target="target" :disabled="disabled">
      <slot />
    </ElAffix>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "FaAffix" });

interface Props {
  /** 固钉偏移距离 */
  offset?: number;
  /** 固钉定位的父级 CSS 选择器 */
  target?: string;
  /** 是否禁用固钉 */
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), { offset: 0 });
</script>
