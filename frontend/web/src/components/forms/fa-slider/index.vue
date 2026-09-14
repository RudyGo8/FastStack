<template>
  <div class="fa-slider">
    <ElSlider
      v-model="sliderValue"
      :min="min"
      :max="max"
      :step="step"
      :disabled="disabled"
      :show-input="showInput"
      :show-input-controls="showInputControls"
      :show-stops="showStops"
      :show-tooltip="showTooltip"
      :range="range"
      v-bind="$attrs"
    />
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "FaSlider" });

const emit = defineEmits<{
  (e: "update:modelValue", value: number | number[]): void;
  (e: "change", value: number | number[]): void;
}>();

interface Props {
  modelValue?: number | number[];
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  showInput?: boolean;
  showInputControls?: boolean;
  showStops?: boolean;
  showTooltip?: boolean;
  range?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: 0,
  min: 0,
  max: 100,
  step: 1,
  disabled: false,
  showInput: false,
  showInputControls: true,
  showStops: false,
  showTooltip: true,
  range: false,
});

const sliderValue = computed({
  get: () => props.modelValue,
  set: (val: number | number[]) => {
    emit("update:modelValue", val);
  },
});
</script>

<style lang="scss" scoped>
.fa-slider {
  width: 100%;
}
</style>
