<template>
  <div class="fa-select-v2">
    <ElSelectV2
      v-model="selectedValue"
      :options="options"
      :placeholder="placeholder"
      :clearable="clearable"
      :filterable="filterable"
      :multiple="multiple"
      :collapse-tags="collapseTags"
      v-bind="$attrs"
      @change="handleChange"
    >
      <template v-if="$slots.prefix" #prefix><slot name="prefix" /></template>
      <template v-if="$slots.empty" #empty><slot name="empty" /></template>
    </ElSelectV2>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

defineOptions({ name: "FaSelectV2" });

interface Props {
  modelValue?: any;
  options?: any[];
  placeholder?: string;
  clearable?: boolean;
  filterable?: boolean;
  multiple?: boolean;
  collapseTags?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  options: () => [],
  placeholder: "请选择",
  clearable: true,
  filterable: true,
  multiple: false,
  collapseTags: true,
});

interface Emits {
  "update:modelValue": [value: any];
  change: [value: any];
}

const emit = defineEmits<Emits>();

const selectedValue = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

function handleChange(val: any) {
  emit("change", val);
}
</script>
