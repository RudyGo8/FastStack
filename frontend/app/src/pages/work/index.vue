<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { useTicketStats } from '@/composables/useTicketStats'
import { useUserStore } from '@/store/userStore'

const { t } = useI18n()

useShare({
  title: t('work.shareTitle'),
  path: '/pages/work/index',
})

definePage({
  name: 'work',
  layout: 'tabbar',
  style: { navigationBarTitleText: '工作台' },
})
useI18nNavTitle('work.navTitle')

const router = useRouter()
const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo)
function navigateTo(name: string) {
  router.push({ name })
}

/** 工单统计（共享缓存，与 mine 页面复用，仅预热缓存，展示在 mine 页） */
const { loadTicketStats } = useTicketStats()

useTabbarActive('pages/work/index', 'work', loadTicketStats)

const groups = [
  {
    titleKey: 'work.businessCenter',
    color: 'var(--wot-orange-6)',
    bg: 'wot-bg-orange-1',
    items: [
      { icon: 'notification', titleKey: 'common.nav.notices', name: 'work-notices' },
      { icon: 'message', titleKey: 'common.nav.tickets', name: 'work-tickets' },
    ],
  },
  {
    titleKey: 'work.devTools',
    color: 'var(--wot-purple-6)',
    bg: 'wot-bg-purple-1',
    items: [
      { icon: 'message', titleKey: 'common.nav.aiChat', name: 'work-chat' },
      { icon: 'robot', titleKey: 'common.nav.aiModels', name: 'work-ai-models' },
    ],
  },
]

/** 搜索关键词，本地过滤模块分组 */
const keyword = ref('')
const filteredGroups = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw)
    return groups
  return groups
    .map(group => ({ ...group, items: group.items.filter(item => t(item.titleKey).toLowerCase().includes(kw)) }))
    .filter(group => group.items.length > 0)
})
</script>

<template>
  <view class="tabbar-wraper py-3">
    <!-- 用户信息卡（品牌渐变 + 极光装饰圆环） -->
    <view class="user-info-card mx-3 mb-4 flex items-center gap-4 rounded-3 px-5 py-6">
      <wd-avatar
        size="64px"
        round
        :src="userInfo?.avatar || ''"
        icon="user"
      />
      <view class="min-w-0 flex-1">
        <view class="text-4 text-white font-bold">
          {{ userInfo?.name || t('work.nameFallback') }}
        </view>
        <view class="mt-1 truncate text-3" style="color: rgba(255, 255, 255, 0.75);">
          {{ userInfo?.roles?.map(r => r.name).join(', ') || t('work.roleFallback') }}
        </view>
      </view>
    </view>

    <!-- 模块搜索 -->
    <view class="mx-3 mb-4">
      <wd-search v-model="keyword" :placeholder="t('work.searchPlaceholder')" variant="light" hide-cancel />
    </view>

    <!-- 模块分组 -->
    <view v-for="(group, gi) in filteredGroups" :key="gi" class="mb-4">
      <view class="mb-2 mt-1 flex items-center gap-2 px-3">
        <view class="h-3.5 w-1 rounded-full" :style="{ backgroundColor: group.color }" />
        <wd-text class="wot-text-text-main text-3.5" :text="t(group.titleKey)" bold />
        <wd-text class="wot-text-text-auxiliary text-2.5" :text="group.items.length" />
      </view>
      <wd-cell-group border custom-class="mx-3 rounded-2! overflow-hidden">
        <wd-cell
          v-for="item in group.items"
          :key="item.name"
          center
          is-link
          @click="navigateTo(item.name)"
        >
          <template #title>
            <view class="flex items-center gap-2.5">
              <view
                class="h-8 w-8 flex shrink-0 items-center justify-center rounded-lg"
                :class="group.bg"
              >
                <wd-icon :name="item.icon" size="16px" :color="group.color" />
              </view>
              <text>
                {{ t(item.titleKey) }}
              </text>
            </view>
          </template>
        </wd-cell>
      </wd-cell-group>
    </view>

    <!-- 搜索无结果 -->
    <wd-empty v-if="filteredGroups.length === 0" :tip="t('work.emptyTip')" />
  </view>
</template>
