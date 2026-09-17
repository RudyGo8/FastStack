<!-- 公告通知：卡片展示布局 -->
<template>
  <div class="notice-card-page">
    <!-- 顶部搜索栏 -->
    <div class="notice-toolbar">
      <div class="toolbar-left">
        <ElInput
          v-model="searchForm.notice_title"
          placeholder="搜索通知标题..."
          clearable
          class="search-input"
          @clear="applySearch"
          @keyup.enter="applySearch"
        >
          <template #prefix>
            <ElIcon><Search /></ElIcon>
          </template>
        </ElInput>

        <ElSelect
          v-model="searchForm.notice_type"
          placeholder="类型"
          clearable
          class="filter-select"
          @change="applySearch"
        >
          <ElOption
            v-for="item in noticeTypeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>

        <ElSelect
          v-model="searchForm.status"
          placeholder="状态"
          clearable
          class="filter-select"
          @change="applySearch"
        >
          <ElOption label="启用" :value="0" />
          <ElOption label="停用" :value="1" />
        </ElSelect>
      </div>

      <div class="toolbar-right">
        <ElButton :icon="Refresh" @click="refreshData">刷新</ElButton>
        <ElButton
          v-if="hasCreatePermission"
          type="primary"
          :icon="Plus"
          :loading="createLoading"
          @click="handleAdd"
        >
          新增通知
        </ElButton>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-loading="loading" class="notice-grid">
      <div v-if="!data.length && !loading" class="empty-state">
        <ElEmpty description="暂无通知" />
      </div>

      <div
        v-for="item in data"
        :key="item.id"
        class="notice-card"
        :class="{ 'is-disabled': item.status === 1 }"
        @click="openDetail(item.id!)"
      >
        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="card-title-row">
            <ElTag
              :type="item.notice_type === '1' ? 'primary' : 'warning'"
              size="small"
              class="type-tag"
            >
              {{ noticeTypeLabel(item.notice_type) }}
            </ElTag>
            <ElTag v-if="item.status === 1" type="danger" size="small" class="status-tag">
              已停用
            </ElTag>
          </div>
          <h3 class="card-title">{{ item.notice_title }}</h3>
        </div>

        <!-- 卡片内容 -->
        <div class="card-body">
          <p class="card-description">
            {{ item.description || stripHtml(item.notice_content) || "暂无描述" }}
          </p>
        </div>

        <!-- 卡片底部 -->
        <div class="card-footer">
          <div class="card-meta">
            <span class="meta-author">{{ item.created_by?.name || "未知" }}</span>
            <span class="meta-time">{{ formatTime(item.created_time) }}</span>
          </div>

          <!-- 操作按钮（仅管理员可见） -->
          <div v-if="hasEditPermission || hasDeletePermission" class="card-actions" @click.stop>
            <ElButton
              v-if="hasEditPermission"
              text
              size="small"
              :icon="Edit"
              @click="handleEdit(item.id!)"
            />
            <ElButton
              v-if="hasDeletePermission"
              text
              size="small"
              type="danger"
              :icon="Delete"
              @click="handleDelete(item.id!, item.notice_title!)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="pagination.total > 0" class="pagination-wrapper">
      <ElPagination
        v-model:current-page="pagination.page_no"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[12, 24, 48]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 详情弹窗 -->
    <ElDialog
      v-model="detailVisible"
      title="通知详情"
      width="720px"
      :close-on-click-modal="false"
    >
      <div v-if="detailData" class="detail-content">
        <div class="detail-header">
          <ElTag
            :type="detailData.notice_type === '1' ? 'primary' : 'warning'"
            class="detail-type-tag"
          >
            {{ noticeTypeLabel(detailData.notice_type) }}
          </ElTag>
          <h2 class="detail-title">{{ detailData.notice_title }}</h2>
        </div>

        <div class="detail-meta">
          <span>创建人：{{ detailData.created_by?.name || "未知" }}</span>
          <span>创建时间：{{ formatTime(detailData.created_time) }}</span>
          <span v-if="detailData.updated_time">
            更新时间：{{ formatTime(detailData.updated_time) }}
          </span>
        </div>

        <ElDivider />

        <div v-if="detailData.description" class="detail-description">
          <h4>摘要</h4>
          <p>{{ detailData.description }}</p>
        </div>

        <div class="detail-body">
          <h4>内容</h4>
          <FaMarkdownRenderer :content="detailData.notice_content || ''" />
        </div>
      </div>
    </ElDialog>

    <!-- 编辑弹窗 -->
    <ElDialog
      v-model="editVisible"
      title="编辑通知"
      width="720px"
      :close-on-click-modal="false"
    >
      <ElForm
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="80px"
        class="edit-form"
      >
        <ElFormItem label="标题" prop="notice_title">
          <ElInput v-model="editForm.notice_title" placeholder="请输入标题" maxlength="50" />
        </ElFormItem>

        <ElFormItem label="描述" prop="description">
          <ElInput
            v-model="editForm.description"
            type="textarea"
            :rows="2"
            maxlength="500"
            show-word-limit
            placeholder="请输入描述"
          />
        </ElFormItem>

        <ElFormItem label="类型" prop="notice_type">
          <ElSelect v-model="editForm.notice_type" placeholder="请选择类型" class="w-full">
            <ElOption
              v-for="item in noticeTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>

        <ElFormItem label="状态" prop="status">
          <ElRadioGroup v-model="editForm.status">
            <ElRadio :value="0">启用</ElRadio>
            <ElRadio :value="1">停用</ElRadio>
          </ElRadioGroup>
        </ElFormItem>

        <ElFormItem label="内容" prop="notice_content">
          <FaWangEditor
            v-model="editForm.notice_content"
            height="300px"
            placeholder="请输入通知内容..."
          />
        </ElFormItem>
      </ElForm>

      <template #footer>
        <ElButton @click="editVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitLoading" @click="submitEdit">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { Delete, Edit, Plus, Refresh, Search } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import NoticeAPI, { type NoticeForm, type NoticeTable } from "@/api/module_system/notice";
import { useDictStore, useNoticeStore, useUserStore } from "@stores";
import FaMarkdownRenderer from "@/components/display/fa-markdown-renderer/index.vue";
import FaWangEditor from "@/components/forms/fa-wang-editor/index.vue";

defineOptions({ name: "Notice" });

const dictStore = useDictStore();
const noticeStore = useNoticeStore();
const userStore = useUserStore();

// 权限判断
const hasCreatePermission = computed(() =>
  userStore.prems.includes("module_system:notice:create")
);
const hasEditPermission = computed(() =>
  userStore.prems.includes("module_system:notice:update")
);
const hasDeletePermission = computed(() =>
  userStore.prems.includes("module_system:notice:delete")
);

// 搜索表单
const searchForm = reactive({
  notice_title: "",
  notice_type: "",
  status: undefined as number | undefined,
});

// 通知类型选项
const noticeTypeOptions = computed(() =>
  dictStore.getDictArray("sys_notice_type").map((item) => ({
    label: item.dict_label,
    value: item.dict_value,
  }))
);

function noticeTypeLabel(val?: string) {
  if (!val) return "";
  const lab = dictStore.getDictLabel("sys_notice_type", val);
  if (typeof lab === "string") return lab;
  return lab.dict_label ?? val;
}

// 数据加载
const loading = ref(false);
const data = ref<NoticeTable[]>([]);
const pagination = reactive({
  page_no: 1,
  page_size: 12,
  total: 0,
});

async function loadData() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page_no: pagination.page_no,
      page_size: pagination.page_size,
    };
    if (searchForm.notice_title) params.notice_title = searchForm.notice_title;
    if (searchForm.notice_type) params.notice_type = searchForm.notice_type;
    if (searchForm.status !== undefined) params.status = searchForm.status;

    const res = await NoticeAPI.listNotice(params);
    if (res.data?.data) {
      data.value = res.data.data.list || [];
      pagination.total = res.data.data.total || 0;
    }
  } catch {
    ElMessage.error("加载通知失败");
  } finally {
    loading.value = false;
  }
}

async function applySearch() {
  pagination.page_no = 1;
  await loadData();
}

async function refreshData() {
  await loadData();
}

function handleSizeChange(size: number) {
  pagination.page_size = size;
  pagination.page_no = 1;
  loadData();
}

function handleCurrentChange(page: number) {
  pagination.page_no = page;
  loadData();
}

// 详情
const detailVisible = ref(false);
const detailData = ref<NoticeTable | null>(null);

async function openDetail(id: number) {
  try {
    const res = await NoticeAPI.detailNotice(id);
    if (res.data?.data) {
      detailData.value = res.data.data;
      detailVisible.value = true;
    }
  } catch {
    ElMessage.error("获取通知详情失败");
  }
}

// 新增
const createLoading = ref(false);

function handleAdd() {
  editForm.id = undefined;
  editForm.notice_title = "";
  editForm.notice_type = "";
  editForm.notice_content = "";
  editForm.status = 0;
  editForm.description = "";
  editVisible.value = true;
}

// 编辑
const editVisible = ref(false);
const editFormRef = ref();
const editForm = reactive<NoticeForm>({
  id: undefined,
  notice_title: "",
  notice_type: "",
  notice_content: "",
  status: 0,
  description: "",
});
const submitLoading = ref(false);

const editRules = {
  notice_title: [{ required: true, message: "请输入标题", trigger: "blur" }],
  notice_type: [{ required: true, message: "请选择类型", trigger: "change" }],
  notice_content: [{ required: true, message: "请输入内容", trigger: "blur" }],
};

function handleEdit(id: number) {
  // 先获取详情再编辑
  openDetailForEdit(id);
}

async function openDetailForEdit(id: number) {
  try {
    const res = await NoticeAPI.detailNotice(id);
    if (res.data?.data) {
      const item = res.data.data;
      editForm.id = item.id;
      editForm.notice_title = item.notice_title || "";
      editForm.notice_type = item.notice_type || "";
      editForm.notice_content = item.notice_content || "";
      editForm.status = item.status ?? 0;
      editForm.description = item.description || "";
      editVisible.value = true;
    }
  } catch {
    ElMessage.error("获取通知详情失败");
  }
}

async function submitEdit() {
  if (!editFormRef.value) return;
  await editFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return;
    submitLoading.value = true;
    try {
      if (editForm.id) {
        await NoticeAPI.updateNotice(editForm.id, editForm);
        ElMessage.success("更新成功");
      } else {
        await NoticeAPI.createNotice(editForm);
        ElMessage.success("创建成功");
      }
      editVisible.value = false;
      await noticeStore.getNotice(true);
      await loadData();
    } catch {
      ElMessage.error("保存失败");
    } finally {
      submitLoading.value = false;
    }
  });
}

// 删除
async function handleDelete(id: number, title: string) {
  try {
    await ElMessageBox.confirm(`确定删除「${title}」吗？`, "提示", {
      type: "warning",
    });
    await NoticeAPI.deleteNotice([id]);
    ElMessage.success("删除成功");
    await noticeStore.getNotice(true);
    await loadData();
  } catch {
    // 取消删除
  }
}

// 工具函数
function formatTime(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function stripHtml(html?: string) {
  if (!html) return "";
  return html.replace(/<[^>]*>/g, "").substring(0, 100);
}

onMounted(async () => {
  await dictStore.getDict(["sys_notice_type"]);
  await loadData();
});
</script>

<style scoped>
.notice-card-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
  background: #f5f7fa;
}

/* 工具栏 */
.notice-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 280px;
}

.filter-select {
  width: 120px;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

/* 卡片网格 */
.notice-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  overflow-y: auto;
  padding-bottom: 16px;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  background: #fff;
  border-radius: 8px;
}

/* 卡片样式 */
.notice-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #eef2f6;
}

.notice-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
  border-color: #d0e3ff;
}

.notice-card.is-disabled {
  opacity: 0.7;
  background: #fafafa;
}

.card-header {
  margin-bottom: 12px;
}

.card-title-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.type-tag {
  font-size: 11px;
}

.status-tag {
  font-size: 11px;
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-body {
  flex: 1;
  margin-bottom: 16px;
}

.card-description {
  margin: 0;
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.card-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-author {
  font-size: 12px;
  color: #333;
  font-weight: 500;
}

.meta-time {
  font-size: 11px;
  color: #999;
}

.card-actions {
  display: flex;
  gap: 4px;
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 16px 0 8px;
  background: #fff;
  border-radius: 8px;
  margin-top: 16px;
}

/* 详情弹窗 */
.detail-content {
  padding: 8px 0;
}

.detail-header {
  margin-bottom: 16px;
}

.detail-type-tag {
  margin-bottom: 12px;
}

.detail-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
}

.detail-meta {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: #666;
}

.detail-description {
  margin-bottom: 20px;
}

.detail-description h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.detail-description p {
  margin: 0;
  font-size: 14px;
  color: #555;
  line-height: 1.6;
}

.detail-body h4 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

/* 编辑表单 */
.edit-form {
  padding: 8px 0;
}
</style>
