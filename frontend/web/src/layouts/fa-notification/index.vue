<!-- 通知组件：铃铛点击直接打开抽屉，卡片展示通知，已读后红点消失 -->
<template>
  <div>
    <!-- 通知列表抽屉 -->
    <ElDrawer v-model="drawerVisible" title="全部通知" size="480px" :close-on-click-modal="true">
      <div v-loading="drawerLoading" class="notice-drawer-content">
        <div v-if="!allNotices.length && !drawerLoading" class="empty-state">
          <ElEmpty description="暂无通知" />
        </div>

        <div
          v-for="item in allNotices"
          :key="item.id"
          class="notice-item"
          :class="{ 'is-read': isRead(item.id) }"
          @click="openNoticeDetail(item)"
        >
          <div class="notice-item-header">
            <div class="header-left">
              <ElTag :type="item.notice_type === '2' ? 'warning' : 'primary'" size="small">
                {{ item.notice_type === "2" ? "公告" : "通知" }}
              </ElTag>
              <span v-if="!isRead(item.id)" class="unread-dot" />
            </div>
            <span class="notice-time">{{ formatTime(item.created_time) }}</span>
          </div>
          <h4 class="notice-title">{{ item.notice_title }}</h4>
          <p class="notice-desc">{{ item.description || stripHtml(item.notice_content) }}</p>
        </div>
      </div>
    </ElDrawer>

    <!-- 通知详情对话框 -->
    <ElDialog v-model="detailVisible" title="通知详情" width="600px" @close="handleDetailClose">
      <div v-if="detailNotice" class="notice-detail">
        <div class="detail-header">
          <ElTag :type="detailNotice.notice_type === '2' ? 'warning' : 'primary'">
            {{ detailNotice.notice_type === "2" ? "公告" : "通知" }}
          </ElTag>
          <h3>{{ detailNotice.notice_title }}</h3>
          <p class="detail-meta">
            <span>{{ detailNotice.created_by?.name || "未知" }}</span>
            <span>{{ formatTime(detailNotice.created_time) }}</span>
          </p>
        </div>
        <ElDivider />
        <div class="detail-content">
          <FaMarkdownRenderer :content="detailNotice.notice_content || ''" />
        </div>
      </div>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import NoticeAPI, { type NoticeTable } from "@/api/module_system/notice";
import { useNoticeStore } from "@stores";
import FaMarkdownRenderer from "@/components/display/fa-markdown-renderer/index.vue";

defineOptions({ name: "FaNotification" });

interface Props {
  /** 兼容旧接口：父组件仍传 v-model:value，点击铃铛即打开抽屉 */
  value: boolean;
}

const props = withDefaults(defineProps<Props>(), {});

interface Emits {
  "update:value": [value: boolean];
}

const emit = defineEmits<Emits>();

const noticeStore = useNoticeStore();

const drawerVisible = ref(false);
const drawerLoading = ref(false);
const allNotices = ref<NoticeTable[]>([]);

const detailVisible = ref(false);
const detailNotice = ref<NoticeTable | null>(null);

const fetchAllNotices = async () => {
  drawerLoading.value = true;
  try {
    // available 接口只需登录态，普通用户可访问
    const res = await NoticeAPI.listNoticeAvailable();
    allNotices.value = res.data?.data ?? [];
  } catch {
    allNotices.value = [];
  } finally {
    drawerLoading.value = false;
  }
};

const isRead = (id?: number) => (id === undefined ? true : noticeStore.readIds.includes(id));

const openNoticeDetail = (item: NoticeTable) => {
  detailNotice.value = item;
  detailVisible.value = true;
  drawerVisible.value = false;
  // 标记已读：红点消失，铃铛角标同步减少
  noticeStore.markAsRead(item.id);
};

const handleDetailClose = () => {
  detailVisible.value = false;
  detailNotice.value = null;
};

const formatTime = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const stripHtml = (html?: string) => {
  if (!html) return "";
  return html.replace(/<[^>]*>/g, "").substring(0, 100);
};

// 铃铛点击 → 直接打开抽屉
watch(
  () => props.value,
  (open) => {
    if (open) {
      drawerVisible.value = true;
      fetchAllNotices();
      emit("update:value", false); // 立即复位，下次点击铃铛可再次触发
    }
  }
);
</script>

<style scoped>
.notice-drawer-content {
  padding: 8px 0;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.notice-item {
  padding: 16px;
  margin-bottom: 12px;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #eef2f6;
}

.notice-item:hover {
  background: #f1f5f9;
  border-color: #d0e3ff;
  transform: translateX(4px);
}

.notice-item.is-read {
  opacity: 0.75;
  background: #fff;
}

.notice-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
}

.notice-time {
  font-size: 12px;
  color: #999;
}

.notice-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.4;
}

.notice-item.is-read .notice-title {
  font-weight: 500;
  color: #555;
}

.notice-desc {
  margin: 0;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 通知详情样式 */
.notice-detail {
  padding: 8px 0;
}

.detail-header {
  margin-bottom: 16px;
}

.detail-header h3 {
  margin: 12px 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.detail-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #666;
}

.detail-content {
  font-size: 14px;
  line-height: 1.7;
  color: #333;
}
</style>
