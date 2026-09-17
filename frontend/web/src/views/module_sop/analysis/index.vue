<template>
  <div class="fa-full-height sop-workspace sop-page">
    <section class="sop-panel pending-panel">
      <el-result icon="info" title="预测校验功能未接入" sub-title="AI 预测数据将由其他部门统一接入，届时本页面将提供 AI 预测与提报预测的对比校验能力">
        <template #extra>
          <div class="pending-plan">
            <h4>后期接入后的规划</h4>
            <p>· 接入 AI 预测数据表（由数据团队提供）</p>
            <p>· 提报预测 vs AI 基线对比矩阵（偏差 >5% 黄色预警、>15% 重点偏离）</p>
            <p>· 差异归因清单与校验证据表</p>
          </div>
        </template>
      </el-result>
    </section>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "SopAnalysis" });
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
