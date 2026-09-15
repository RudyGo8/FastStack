<template>
  <div class="fa-full-height sop-workspace sop-page knowledge-page">
    <el-card shadow="never" class="knowledge-metrics">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-statistic title="文档数量" :value="metrics.documentCount" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="切片总数" :value="metrics.chunkCount" />
        </el-col>
        <el-col :span="8">
          <div class="knowledge-status">
            <span>索引状态</span><strong>{{ metrics.indexStatus }}</strong>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="knowledge-library">
      <template #header>
        <div class="flex items-center justify-between">
          <span>知识库文档（解析后入向量库，供智能问答检索）</span>
          <div class="flex gap-2">
            <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
            <el-upload
              :show-file-list="false"
              :http-request="handleBatchUpload"
              accept=".pdf,.docx,.doc,.xlsx,.xls"
              multiple
              :disabled="uploading"
            >
              <el-button type="primary" :loading="uploading" :icon="Upload">批量上传</el-button>
            </el-upload>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="documents" border stripe>
        <el-table-column label="文件" min-width="300">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <el-icon
                :size="18"
                :color="
                  getFilePresentation(row.filename).tone === 'danger'
                    ? '#f56c6c'
                    : getFilePresentation(row.filename).tone === 'primary'
                      ? '#409eff'
                      : getFilePresentation(row.filename).tone === 'success'
                        ? '#67c23a'
                        : '#909399'
                "
              >
                <component :is="getFilePresentation(row.filename).icon" />
              </el-icon>
              <span class="text-truncate" :title="row.filename">{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="
                getFilePresentation(row.filename).tone === 'danger'
                  ? 'danger'
                  : getFilePresentation(row.filename).tone === 'success'
                    ? 'success'
                    : 'info'
              "
            >
              {{ getFilePresentation(row.filename).extension }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="切片数" width="100" align="right" />
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="openChunkDrawer(row.filename)"
              >查看分块</el-button
            >
            <el-popconfirm
              title="删除后向量数据不可恢复，确定？"
              @confirm="handleDelete(row.filename)"
            >
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无文档，上传 PDF/Word/Excel 后自动解析" />
        </template>
      </el-table>

      <div v-if="loadError" class="mt-3 text-sm text-red-500">{{ loadError }}</div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="`分块预览：${drawerFilename}`" size="50%">
      <div v-loading="drawerLoading">
        <el-empty v-if="!drawerLoading && drawerChunks.length === 0" description="暂无分块数据" />
        <div v-for="chunk in drawerChunks" :key="chunk.chunk_id" class="chunk-item mb-3">
          <div class="flex items-center gap-2 mb-1">
            <el-tag size="small">#{{ chunk.chunk_idx }}</el-tag>
            <el-tag v-if="chunk.page_number" size="small" type="info"
              >P{{ chunk.page_number }}</el-tag
            >
            <el-tag size="small" type="warning">L{{ chunk.chunk_level }}</el-tag>
          </div>
          <pre class="chunk-text">{{ chunk.text_preview }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { Refresh, Upload } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";

import { SopDocumentAPI } from "@/api/module_ai/document";
import type { SopDocumentChunk, SopDocumentInfo } from "@/api/module_sop/types";
import { buildKnowledgeMetrics, getFilePresentation } from "@/views/module_sop/shared/presentation";

defineOptions({ name: "SopKnowledge" });

const documents = ref<SopDocumentInfo[]>([]);
const loading = ref(false);
const uploading = ref(false);
const loadError = ref("");

const metrics = computed(() => buildKnowledgeMetrics(documents.value));

const drawerVisible = ref(false);
const drawerFilename = ref("");
const drawerChunks = ref<SopDocumentChunk[]>([]);
const drawerLoading = ref(false);

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await SopDocumentAPI.list();
    documents.value = res.data?.data?.documents ?? [];
  } catch (e: any) {
    loadError.value = e?.response?.data?.detail || e?.message || "加载文档列表失败";
  } finally {
    loading.value = false;
  }
}

async function handleBatchUpload(option: any) {
  const files = option.file;
  if (!files) return;
  const fileList = Array.isArray(files) ? files : [files];
  uploading.value = true;
  try {
    const res = await SopDocumentAPI.batchUpload(fileList);
    const data = res.data?.data;
    if (data) {
      ElMessage.success(
        `上传完成：${data.succeeded} 成功${data.failed > 0 ? `，${data.failed} 失败` : ""}`
      );
    } else {
      ElMessage.success("上传成功");
    }
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || "上传失败");
  } finally {
    uploading.value = false;
  }
}

async function handleDelete(filename: string) {
  try {
    await SopDocumentAPI.delete(filename);
    ElMessage.success("已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || "删除失败");
  }
}

async function openChunkDrawer(filename: string) {
  drawerFilename.value = filename;
  drawerChunks.value = [];
  drawerVisible.value = true;
  drawerLoading.value = true;
  try {
    const res = await SopDocumentAPI.getChunks(filename);
    drawerChunks.value = res.data?.data?.chunks ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "获取分块数据失败");
  } finally {
    drawerLoading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.knowledge-metrics,
.knowledge-library {
  margin: 0;
  border-color: #e6ebf2;
  border-radius: 8px;
  box-shadow: none;
}
.knowledge-metrics :deep(.el-card__body) {
  padding: 14px 18px;
}
.knowledge-library {
  flex: 1;
}
.knowledge-status {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.knowledge-status span {
  color: #64748b;
  font-size: 12px;
}
.knowledge-status strong {
  color: #13a894;
  font-size: 20px;
}
.chunk-text {
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}
.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
