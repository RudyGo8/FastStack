<!-- 自动完成组件 -->
<template>
  <div class="fa-autocomplete">
    <ElAutocomplete
      v-model="inputValue"
      :fetch-suggestions="onSearch"
      :placeholder="placeholder"
      :debounce="debounce"
      :clearable="clearable"
      v-bind="$attrs"
      @select="handleSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

defineOptions({ name: "FaAutocomplete" });

interface Props {
  modelValue?: string;
  placeholder?: string;
  fetchSuggestions?: (queryString: string) => Promise<any[]>;
  debounce?: number;
  clearable?: boolean;
  valueKey?: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  placeholder: "请输入",
  debounce: 300,
  clearable: true,
  valueKey: "value",
});

interface Emits {
  "update:modelValue": [value: string];
  select: [item: any];
}

const emit = defineEmits<Emits>();

const inputValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (newVal) => {
    inputValue.value = newVal;
  }
);

watch(inputValue, (newVal) => {
  emit("update:modelValue", newVal);
});

async function onSearch(queryString: string, cb: (results: any[]) => void) {
  if (props.fetchSuggestions) {
    const results = await props.fetchSuggestions(queryString);
    cb(results);
  } else {
    cb([]);
  }
}

function handleSelect(item: any) {
  emit("select", item);
}
</script>
