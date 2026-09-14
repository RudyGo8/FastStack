<template>
  <div class="fa-table-v2" :style="{ height: height }">
    <ElTableV2
      :columns="columns"
      :data="data"
      :width="tableWidth"
      :height="tableHeight"
      v-bind="$attrs"
    >
      <slot />
    </ElTableV2>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

defineOptions({ name: "FaTableV2" });

interface Props {
  /** 列配置 */
  columns?: any[];
  /** 表格数据 */
  data?: any[];
  /** 表格宽度 */
  width?: number | string;
  /** 容器高度 */
  height?: string;
}

const props = withDefaults(defineProps<Props>(), {
  columns: () => [],
  data: () => [],
  width: "100%",
  height: "400px",
});

/** ElTableV2 需要数值类型的 width */
const tableWidth = computed(() => {
  return Number(props.width) || 0;
});

/** ElTableV2 需要数值类型的 height，从容器高度 prop 中提取 */
const tableHeight = computed(() => {
  return parseInt(props.height, 10) || 400;
});
</script>

<style lang="scss" scoped>
.fa-table-v2 {
  width: 100%;
}
</style>
