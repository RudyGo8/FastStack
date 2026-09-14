<script lang="ts" setup>
const { enabled: watermarkEnabled, content: watermarkContent, color: watermarkColor } = useWatermark()
</script>

<script lang="ts">
export default {
  options: {
    addGlobalClass: true,
    virtualHost: true,
    styleIsolation: 'shared',
  },
}
</script>

<template>
  <slot />
  <wd-watermark
    v-if="watermarkEnabled"
    :content="watermarkContent"
    :color="watermarkColor"
    :width="130"
    :height="140"
    :opacity="0.4"
    layout="grid"
  />
</template>
