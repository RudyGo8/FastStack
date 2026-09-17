<template>
  <div class="fa-full-height sop-workspace sop-page">
    <section class="sop-panel pending-panel">
      <el-result icon="info" title="市场信息功能未接入" sub-title="待接入可审计的外部市场数据源后，本页面将按来源与时间戳展示行业热点与竞品动态">
        <template #extra>
          <div class="pending-plan">
            <h4>后期接入后的规划</h4>
            <p>· 竞品数据池（dw_bd_competitor_pool）与竞品经销商拿货价格表接入</p>
            <p>· 按来源与时间戳展示行业热点，所有记录保留审计链路</p>
            <p>· 竞品动态与自有 SPU 销量走势的关联分析</p>
          </div>
        </template>
      </el-result>
    </section>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "SopMarket" });
</script>

<style scoped>
.pending-panel {
  display: grid;
  place-items: center;
  min-height: 60vh;
}
.pending-plan {
  max-width: 420px;
  padding: 16px 20px;
  border: 1px solid var(--sop-border, var(--sop-border));
  border-radius: 8px;
  background: var(--sop-subtle);
  text-align: left;
}
.pending-plan h4 {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--sop-title);
}
.pending-plan p {
  margin: 6px 0;
  font-size: 12.5px;
  color: var(--sop-muted);
  line-height: 1.6;
}
</style>
