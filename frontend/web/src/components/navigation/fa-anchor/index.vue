<template>
  <div class="fa-anchor">
    <ElAnchor :container-id="containerId" :offset="offset" :affix="affix" v-bind="$attrs">
      <slot />
    </ElAnchor>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "FaAnchor" });

interface Props {
  /** 滚动容器的 CSS 选择器 */
  containerId: string;
  /** 锚点偏移距离 */
  offset?: number;
  /** 是否固定 */
  affix?: boolean;
}

withDefaults(defineProps<Props>(), {
  offset: 0,
});
</script>
