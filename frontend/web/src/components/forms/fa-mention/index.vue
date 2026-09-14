<template>
  <div class="fa-mention">
    <ElMention
      v-model="content"
      :options="mergedOptions"
      :placeholder="placeholder"
      :prefix="prefix"
      v-bind="$attrs"
      @select="handleSelect"
      @search="handleSearch"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";

defineOptions({ name: "FaMention" });

interface MentionOption {
  value?: string;
  label?: string;
}

interface Props {
  modelValue?: string;
  options?: MentionOption[];
  placeholder?: string;
  prefix?: string;
  fetchOptions?: (query: string) => Promise<MentionOption[]>;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  options: () => [],
  placeholder: "@提及",
  prefix: "@",
});

interface Emits {
  (e: "update:modelValue", val: string): void;
  (e: "select", val: MentionOption): void;
}

const emit = defineEmits<Emits>();

const content = computed({
  get: () => props.modelValue,
  set: (val: string) => emit("update:modelValue", val),
});

const fetchedOptions = ref<MentionOption[]>([]);

const mergedOptions = computed<MentionOption[]>(() => {
  if (fetchedOptions.value.length > 0) {
    return fetchedOptions.value;
  }
  return props.options;
});

function handleSelect(val: MentionOption) {
  fetchedOptions.value = [];
  emit("select", val);
}

async function handleSearch(query: string) {
  if (props.fetchOptions && query) {
    try {
      const result = await props.fetchOptions(query);
      fetchedOptions.value = result;
    } catch (err) {
      console.warn("[FaMention] fetchOptions error:", err);
      fetchedOptions.value = [];
    }
  } else {
    fetchedOptions.value = [];
  }
}
</script>
