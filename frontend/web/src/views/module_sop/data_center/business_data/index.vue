<template>
  <div class="fa-full-height p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>业务数据（只读）</span>
          <el-button :icon="Refresh" circle :loading="loading" @click="loadData" />
        </div>
      </template>

      <div v-loading="loading">
        <el-alert type="info" :closable="false" show-icon class="mb-4">
          <template #title><strong>业务数据概览</strong></template>
          查看 SPU 主数据、销售事实、激活事实与预测数据。数据导入与配置请联系管理员。
        </el-alert>

        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="SPU 主数据" name="spus">
            <el-table :data="spus" border stripe>
              <el-table-column prop="spu_code" label="SPU 编码" width="150" />
              <el-table-column prop="spu_name" label="SPU 名称" min-width="200" />
              <el-table-column prop="product_line" label="产品线" width="150" />
              <el-table-column label="品牌 / 品类" width="200">
                <template #default="{ row }"
                  >{{ row.brand || "—" }} / {{ row.category || "—" }}</template
                >
              </el-table-column>
              <el-table-column prop="lifecycle_stage" label="生命周期" width="120" />
              <template #empty><el-empty description="暂无 SPU 主数据" /></template>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="数据源状态" name="sources">
            <el-table :data="sources" border stripe>
              <el-table-column prop="label" label="数据域" width="140" />
              <el-table-column label="同步状态" width="110">
                <template #default="{ row }"
                  ><el-tag
                    :type="getSourceSyncDisplay(row.ingestion_status, row.phase_scope).type"
                    >{{ getSourceSyncDisplay(row.ingestion_status, row.phase_scope).label }}</el-tag
                  ></template
                >
              </el-table-column>
              <el-table-column prop="latest_snapshot_at" label="最新同步时点" width="180" />
              <el-table-column prop="max_business_date" label="最新业务日期" width="130" />
              <el-table-column prop="record_count" label="记录数" width="100" />
              <el-table-column prop="note" label="说明" min-width="220" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { onMounted, ref } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";
import type { SopSourceStatus, SopSpuInfo } from "@/api/module_sop/types";
import { getSourceSyncDisplay } from "../../shared/report-metrics";

defineOptions({ name: "BusinessData" });

const loading = ref(false);
const activeTab = ref("spus");
const spus = ref<SopSpuInfo[]>([]);
const sources = ref<SopSourceStatus[]>([]);

async function loadData() {
  loading.value = true;
  try {
    const [status, spuResult] = await Promise.all([
      SopDataAPI.getDataStatus(),
      SopDataAPI.getSpuList({ limit: 100 }),
    ]);
    sources.value = status.data?.data?.sources ?? [];
    spus.value = spuResult.data?.data?.items ?? [];
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>
