<template>
  <div class="fa-full-height sop-workspace sop-page">
    <section class="sop-panel market-panel">
      <div class="sop-section-heading market-heading">
        <div>
          <span class="sop-heading-icon">↗</span>
          <div>
            <h2>市场热点</h2>
            <p>按来源与观测时间展示可审计的行业与竞品动态</p>
          </div>
        </div>
        <el-button :icon="Refresh" circle :loading="loading" @click="refresh" />
      </div>

      <div v-loading="loading">
        <template v-if="status === 'unconfigured'">
          <el-result
            icon="info"
            title="外部市场数据源尚未接入"
            sub-title="待接入可审计的外部市场数据源后，本页面将按来源与时间戳展示行业热点与竞品动态，所有记录均保留审计链路"
          >
            <template #extra>
              <el-button type="primary" @click="refresh">刷新重试</el-button>
            </template>
          </el-result>
        </template>

        <template v-else-if="status === 'empty'">
          <el-empty description="暂无市场热点数据" />
        </template>

        <template v-else-if="status === 'ready' && records.length">
          <div class="market-grid">
            <article v-for="(record, i) in records" :key="i" class="market-record">
              <div class="market-record-header">
                <span class="font-bold">{{ record.title }}</span>
                <div class="flex items-center gap-2 text-xs text-gray-500">
                  <el-tag size="small" type="info">{{ record.source }}</el-tag>
                  <span v-if="record.observed_at">{{ formatTime(record.observed_at) }}</span>
                </div>
              </div>
              <p class="text-sm">{{ record.summary }}</p>
              <div v-if="record.impact" class="mt-2">
                <el-tag
                  size="small"
                  :type="
                    record.impact === 'high'
                      ? 'danger'
                      : record.impact === 'medium'
                        ? 'warning'
                        : 'info'
                  "
                >
                  影响：{{ impactLabel(record.impact) }}
                </el-tag>
              </div>
            </article>
          </div>
        </template>

        <template v-else-if="status === 'error'">
          <el-result icon="warning" title="市场数据加载失败" :sub-title="errorMessage">
            <template #extra>
              <el-button type="primary" @click="refresh">重试</el-button>
            </template>
          </el-result>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import { onMounted, ref } from "vue";

import { SopDataAPI } from "@/api/module_sop/data";

defineOptions({ name: "SopMarket" });

interface MarketRecord {
  title: string;
  summary: string;
  source: string;
  observed_at: string | null;
  impact: string | null;
}

const loading = ref(false);
const status = ref<"loading" | "unconfigured" | "empty" | "ready" | "error">("loading");
const records = ref<MarketRecord[]>([]);
const errorMessage = ref("");

const formatTime = (iso: string) =>
  iso ? new Date(iso).toLocaleString("zh-CN", { hour12: false }) : "";
const impactLabel = (impact: string) => ({ high: "高", medium: "中", low: "低" })[impact] ?? impact;

async function refresh() {
  loading.value = true;
  status.value = "loading";
  errorMessage.value = "";
  try {
    const res = await SopDataAPI.getMarketHotspots();
    const data = res.data?.data;
    if (Array.isArray(data) && data.length > 0) {
      records.value = data;
      status.value = "ready";
    } else {
      records.value = [];
      status.value = "empty";
    }
  } catch (e: any) {
    if (e?.response?.status === 501) {
      status.value = "unconfigured";
    } else {
      status.value = "error";
      errorMessage.value = e?.response?.data?.detail || e?.message || "未知错误";
    }
  } finally {
    loading.value = false;
  }
}

onMounted(refresh);
</script>

<style scoped>
.market-heading {
  margin-bottom: 0;
  padding-bottom: 16px;
  border-bottom: 1px solid #eef2f6;
}
.market-heading h2 {
  margin: 0;
  color: #141b2d;
  font-size: 16px;
}
.market-heading p {
  margin: 3px 0 0;
  color: #94a3b8;
  font-size: 12px;
}
.market-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding-top: 14px;
}
.market-record {
  padding: 16px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fafbfc;
}
.market-record-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.market-record p {
  color: #475569;
  line-height: 1.7;
}
@media (max-width: 800px) {
  .market-grid {
    grid-template-columns: 1fr;
  }
}
</style>
