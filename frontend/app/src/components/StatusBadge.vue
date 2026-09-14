<script setup lang="ts">
/**
 * 状态徽标组件
 * 用于统一展示启用/禁用/草稿/发布等状态
 */
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{
  status?: string | boolean | number
  /** 自定义映射: { '0': 'enabled', '1': 'disabled', true: 'enabled', false: 'disabled' } */
  map?: Record<string, string>
  /** 自定义标签文本 */
  label?: string
  /** 仅显示圆点 */
  dot?: boolean
}>(), {
  status: '',
  label: '',
  dot: false,
})

const { t } = useI18n()

const statusMap: Record<string, { labelKey: string, cls: string }> = {
  enabled: { labelKey: 'common.status.enabled', cls: 'status-badge--enabled' },
  disabled: { labelKey: 'common.status.disabled', cls: 'status-badge--disabled' },
  draft: { labelKey: 'common.status.draft', cls: 'status-badge--draft' },
  published: { labelKey: 'common.status.published', cls: 'status-badge--primary' },
  archived: { labelKey: 'common.status.archived', cls: 'status-badge--disabled' },
  active: { labelKey: 'common.status.active', cls: 'status-badge--primary' },
  success: { labelKey: 'common.status.success', cls: 'status-badge--enabled' },
  failed: { labelKey: 'common.status.failed', cls: 'status-badge--danger' },
  pending: { labelKey: 'common.status.pending', cls: 'status-badge--draft' },
  processing: { labelKey: 'common.status.processing', cls: 'status-badge--primary' },
  completed: { labelKey: 'common.status.completed', cls: 'status-badge--enabled' },
  closed: { labelKey: 'common.status.closed', cls: 'status-badge--disabled' },
  deprecated: { labelKey: 'common.status.deprecated', cls: 'status-badge--danger' },
  expired: { labelKey: 'common.status.expired', cls: 'status-badge--danger' },
}

function resolve(input: string | boolean | number): { label: string, cls: string } {
  // 1. 自定义 map 优先（业务状态：如 notices 0=草稿/1=已发布、tickets 0=待处理/1=处理中）
  const mappedKey = props.map?.[String(input)]
  if (mappedKey && statusMap[mappedKey])
    return { label: t(statusMap[mappedKey].labelKey), cls: statusMap[mappedKey].cls }
  // 2. 后端通用规范: 0=启用, 1=禁用
  if (input === true || input === 'true' || input === '1' || input === 1 || input === '0' || input === 0 || input === false || input === 'false') {
    const isEnabled = input === 0 || input === '0' || input === true || input === 'true'
    return isEnabled
      ? { label: t('common.status.enabled'), cls: 'status-badge--enabled' }
      : { label: t('common.status.disabled'), cls: 'status-badge--disabled' }
  }
  // 3. 内置状态映射兜底
  const entry = statusMap[String(input)]
  return entry ? { label: t(entry.labelKey), cls: entry.cls } : { label: String(input), cls: 'status-badge--disabled' }
}
</script>

<template>
  <text v-if="dot" class="status-badge--dot" :class="resolve(status).cls" />
  <text v-else class="status-badge" :class="resolve(status).cls">
    <text class="status-badge--dot" :class="resolve(status).cls" />
    {{ label || resolve(status).label }}
  </text>
</template>

<style lang="scss">
/* 状态徽标全局样式（非 scoped，供页面复用类名）
 * 颜色使用 wot-ui 语义变量，自动适配亮/暗主题 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6rpx;
  padding: 4rpx 14rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
  line-height: 1.4;
}

.status-badge--dot {
  display: inline-block;
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  flex-shrink: 0;
  background: currentColor;
}

/* 各状态仅定义文字色，背景色由带外层 .status-badge 的组合规则提供，
 * 使纯圆点模式只显示纯色圆点 */
.status-badge--enabled {
  @apply wot-text-success-main;
}
.status-badge.status-badge--enabled {
  @apply wot-bg-success-surface;
}

.status-badge--disabled {
  @apply wot-text-text-auxiliary;
}
.status-badge.status-badge--disabled {
  @apply wot-bg-filled-content;
}

.status-badge--primary {
  @apply wot-text-primary-6;
}
.status-badge.status-badge--primary {
  @apply wot-bg-primary-1;
}

.status-badge--danger {
  @apply wot-text-danger-main;
}
.status-badge.status-badge--danger {
  @apply wot-bg-danger-surface;
}

/* failed 为 danger 的别名（menus 页菜单类型使用） */
.status-badge--failed {
  @apply wot-text-danger-main;
}
.status-badge.status-badge--failed {
  @apply wot-bg-danger-surface;
}

.status-badge--draft {
  @apply wot-text-text-secondary;
}
.status-badge.status-badge--draft {
  @apply wot-bg-filled-content;
}
</style>
