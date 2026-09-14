<template>
  <div class="fa-input-tag">
    <ElInputTag
      v-model="tagValue"
      :placeholder="placeholder"
      :clearable="clearable"
      :max="max"
      :disabled="disabled"
      :size="size"
      v-bind="$attrs"
    >
      <template v-if="$slots.prefix" #prefix><slot name="prefix" /></template>
    </ElInputTag>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "FaInputTag" });

interface Props {
  modelValue?: string[];
  placeholder?: string;
  clearable?: boolean;
  max?: number;
  disabled?: boolean;
  size?: "large" | "default" | "small";
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  placeholder: "请输入标签",
  clearable: true,
  disabled: false,
  size: "default",
});

interface Emits {
  (e: "update:modelValue", value: string[]): void;
  (e: "change", value: string[]): void;
}

const emit = defineEmits<Emits>();

const tagValue = computed({
  get: () => props.modelValue,
  set: (value: string[]) => {
    emit("update:modelValue", value);
    emit("change", value);
  },
});
</script>
