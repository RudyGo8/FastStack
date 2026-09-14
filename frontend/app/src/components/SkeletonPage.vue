<script setup lang="ts">
/**
 * 页面骨架屏组件
 * 在数据加载时展示占位内容，提升感知性能
 * 基于 wd-skeleton 封装
 */
const props = withDefaults(defineProps<{
  /** 显示行数（列表行） */
  rows?: number
  /** 是否显示搜索栏骨架 */
  search?: boolean
  /** 是否显示操作栏骨架 */
  action?: boolean
}>(), {
  rows: 5,
})

/** 搜索栏占位行 */
const searchRowCol = [{ type: 'rect' as const, height: '64rpx', borderRadius: '12rpx' }]

/** 列表行占位：圆形头像 + 文本块 + 右侧徽章 */
const listRowCol = [
  [
    { type: 'circle' as const, size: '64rpx' },
    { type: 'rect' as const, width: '200rpx', height: '28rpx', marginLeft: '24rpx' },
    { type: 'rect' as const, width: '80rpx', height: '40rpx', borderRadius: '999rpx' },
  ],
]
</script>

<template>
  <view class="p-sm">
    <!-- 搜索栏骨架 -->
    <view v-if="search" class="admin-card mb-md p-md">
      <wd-skeleton :row-col="searchRowCol" :loading="true" animation="gradient" />
    </view>
    <!-- 多行列表骨架 -->
    <view class="admin-card p-sm">
      <view v-for="i in props.rows" :key="i" class="gap-md p-md">
        <wd-skeleton :row-col="listRowCol" :loading="true" animation="gradient" />
      </view>
    </view>
  </view>
</template>
