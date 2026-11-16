<template>
  <div class="fa-full-height sop-workspace sop-page knowledge-page">
    <el-card shadow="never" class="knowledge-metrics">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-statistic title="文档数量" :value="documents.length" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="分块总数" :value="chunkTotal" />
        </el-col>
        <el-col :span="8">
          <div class="knowledge-status"><span>检索模式</span><strong>向量 + 词项混合</strong></div>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="knowledge-library">
      <template #header>
        <div class="flex items-center justify-between">
          <span>向量知识库（文本入库后供检索，父子分块保留上下文）</span>
          <div class="flex gap-2">
            <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
            <el-upload
              :show-file-list="false"
              :http-request="handleUpload"
              accept=".txt,.md,.markdown"
              multiple
              :disabled="uploading"
            >
              <el-button type="primary" :loading="uploading" :icon="Upload">上传文本</el-button>
            </el-upload>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="documents" border stripe>
        <el-table-column prop="filename" label="文件" min-width="280" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.file_type || "txt" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunks" label="分块数" width="100" align="right" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
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
          <el-empty description="暂无文档，上传 .txt / .md 后自动分块并生成向量" />
        </template>
      </el-table>

      <div v-if="loadError" class="mt-3 text-sm text-red-500">{{ loadError }}</div>
    </el-card>

    <el-card shadow="never" class="knowledge-search mt-4">
      <template #header>
        <span>检索测试</span>
      </template>
      <div class="flex gap-2 mb-3">
        <el-input
          v-model="query"
          placeholder="输入问题，验证召回与来源引用"
          clearable
          @keyup.enter="handleSearch"
        />
        <el-button
          type="primary"
          :loading="searching"
          :disabled="!query.trim()"
          @click="handleSearch"
        >
          检索
        </el-button>
      </div>

      <el-empty v-if="searched && hits.length === 0" description="没有命中任何分块" />
      <div v-for="hit in hits" :key="hit.chunk_id" class="chunk-item mb-3">
        <div class="flex items-center gap-2 mb-1">
          <el-tag size="small" type="success">{{ hit.filename }}</el-tag>
          <el-tag v-if="hit.page_number" size="small" type="info">P{{ hit.page_number }}</el-tag>
          <el-tag size="small">score {{ hit.score.toFixed(4) }}</el-tag>
        </div>
        <pre class="chunk-text">{{ hit.parent_text || hit.text }}</pre>
      </div>
      <div v-if="sources.length" class="mt-2 text-sm text-g-600">
        来源：{{ sources.join("、") }}
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Refresh, Upload } from "@element-plus/icons-vue";
import type { UploadRequestOptions } from "element-plus";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";

import type { RagDocument, RagHit } from "@/api/module_ai/rag";
import { RagAPI } from "@/api/module_ai/rag";

defineOptions({ name: "AiRag" });

const documents = ref<RagDocument[]>([]);
const loading = ref(false);
const uploading = ref(false);
const loadError = ref("");

const query = ref("");
const hits = ref<RagHit[]>([]);
const sources = ref<string[]>([]);
const searching = ref(false);
const searched = ref(false);

const chunkTotal = computed(() =>
  documents.value.reduce((sum, item) => sum + (item.chunks || 0), 0)
);

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await RagAPI.documents();
    documents.value = res.data?.data?.documents ?? [];
  } catch (e: any) {
    loadError.value = e?.response?.data?.msg || e?.message || "加载文档列表失败";
  } finally {
    loading.value = false;
  }
}

async function handleUpload(options: UploadRequestOptions) {
  const file = options.file as File;
  uploading.value = true;
  try {
    const content = await file.text();
    const res = await RagAPI.ingest({
      filename: file.name,
      content,
      file_type: file.name.split(".").pop() || "txt",
    });
    const data = res.data?.data;
    ElMessage.success(`${file.name} 入库完成：${data?.chunks ?? 0} 个分块`);
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || `${file.name} 入库失败`);
  } finally {
    uploading.value = false;
  }
}

async function handleDelete(filename: string) {
  try {
    await RagAPI.remove(filename);
    ElMessage.success(`已删除 ${filename}`);
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || "删除失败");
  }
}

async function handleSearch() {
  if (!query.value.trim()) return;
  searching.value = true;
  searched.value = false;
  try {
    const res = await RagAPI.search({ query: query.value.trim() });
    hits.value = res.data?.data?.hits ?? [];
    sources.value = res.data?.data?.sources ?? [];
    searched.value = true;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || "检索失败");
  } finally {
    searching.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.chunk-item {
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.chunk-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: break-word;
  white-space: pre-wrap;
}
</style>
