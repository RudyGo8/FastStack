<template>
  <div class="fa-tree-v2" :style="{ height: height }">
    <ElTreeV2
      :data="data"
      :props="treeProps"
      :height="computedHeight"
      :highlight-current="highlightCurrent"
      :default-expand-all="defaultExpandAll"
      v-bind="$attrs"
    >
      <slot />
    </ElTreeV2>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

defineOptions({ name: "FaTreeV2" });

interface Props {
  data?: Record<string, any>[];
  height?: string;
  emptyText?: string;
  highlightCurrent?: boolean;
  defaultExpandAll?: boolean;
  nodeKey?: string;
  /** 节点 label 字段名 */
  label?: string;
  /** 节点 children 字段名 */
  children?: string;
}

const props = withDefaults(defineProps<Props>(), {
  data: () => [],
  height: "400px",
  highlightCurrent: true,
  defaultExpandAll: false,
  nodeKey: "id",
  label: "label",
  children: "children",
});

const treeProps = computed(() => ({
  label: props.label,
  children: props.children,
}));

const computedHeight = computed(() => {
  const parsed = parseInt(props.height, 10);
  return isNaN(parsed) ? 400 : parsed;
});
</script>
