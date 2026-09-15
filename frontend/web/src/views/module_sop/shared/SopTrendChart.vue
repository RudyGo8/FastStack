<template><div ref="chartEl" class="sop-trend-chart" /></template>

<script setup lang="ts">
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { SopTrendPoint } from "@/api/module_sop/types";

echarts.use([
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
  LineChart,
  CanvasRenderer,
]);
const props = defineProps<{ data: SopTrendPoint[] }>();
const chartEl = ref<HTMLDivElement>();
let chart: echarts.ECharts | undefined;
let observer: ResizeObserver | undefined;

function render(): void {
  if (!chartEl.value) return;
  chart ??= echarts.init(chartEl.value);
  const firstForecastIndex = props.data.findIndex((item) => item.type === "forecast");
  const forecastStart =
    firstForecastIndex >= 0 ? props.data[firstForecastIndex]?.period : undefined;
  const forecastEnd = props.data.at(-1)?.period;
  chart.setOption(
    {
      animationDuration: 420,
      color: ["#2563eb", "#0ea5e9", "#8b5cf6", "#f59e0b", "#ef4444"],
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, .92)",
        borderWidth: 0,
        textStyle: { color: "#fff", fontSize: 11 },
      },
      legend: {
        bottom: 0,
        itemWidth: 14,
        itemHeight: 7,
        textStyle: { color: "#64748b", fontSize: 10 },
      },
      grid: { left: 58, right: 22, top: 26, bottom: 58 },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: props.data.map((item) => item.period),
        axisLine: { lineStyle: { color: "#dbe4f0" } },
        axisTick: { show: false },
        axisLabel: { rotate: 42, color: "#64748b", fontSize: 9.5, margin: 12 },
      },
      yAxis: {
        type: "value",
        name: "单位：台",
        nameTextStyle: { color: "#64748b", fontSize: 10, padding: [0, 0, 4, 0] },
        axisLabel: { color: "#64748b", fontSize: 9.5 },
        splitLine: { lineStyle: { color: "#eef2f6", type: "dashed" } },
      },
      series: [
        {
          name: "销售出库数量",
          type: "line",
          smooth: 0.22,
          symbolSize: 4,
          lineStyle: { width: 2.5 },
          areaStyle: { opacity: 0.055 },
          data: props.data.map((item) => item.outbound_qty),
        },
        {
          name: "激活数量",
          type: "line",
          smooth: 0.22,
          symbolSize: 4,
          lineStyle: { width: 2 },
          data: props.data.map((item) => item.activation_qty),
        },
        {
          name: "AI预测出库数量",
          type: "line",
          smooth: 0.22,
          symbol: "diamond",
          symbolSize: 4,
          lineStyle: { width: 1.7, type: "dashed" },
          data: props.data.map((item) => item.ai_forecast_outbound),
        },
        {
          name: "AI预测激活数量",
          type: "line",
          smooth: 0.22,
          symbol: "diamond",
          symbolSize: 4,
          lineStyle: { width: 1.7, type: "dashed" },
          data: props.data.map((item) => item.ai_forecast_activation),
        },
        {
          name: "提报预测出库数量",
          type: "line",
          smooth: 0.22,
          symbolSize: 4,
          lineStyle: { width: 2.4 },
          data: props.data.map((item) => item.submit_forecast),
          markArea:
            forecastStart && forecastEnd
              ? {
                  silent: true,
                  itemStyle: { color: "rgba(139, 92, 246, .045)" },
                  data: [[{ xAxis: forecastStart }, { xAxis: forecastEnd }]],
                }
              : undefined,
          markLine: forecastStart
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { color: "#8b5cf6", width: 1.2, type: "dashed" },
                label: {
                  formatter: "未来6个月预测",
                  color: "#7c3aed",
                  fontSize: 9,
                  position: "insideEndTop",
                },
                data: [{ xAxis: forecastStart }],
              }
            : undefined,
        },
      ],
    },
    true
  );
}

onMounted(() => {
  render();
  if (typeof ResizeObserver !== "undefined" && chartEl.value) {
    observer = new ResizeObserver(() => chart?.resize());
    observer.observe(chartEl.value);
  }
});
watch(() => props.data, render, { deep: true });
onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
});
</script>

<style scoped>
.sop-trend-chart {
  width: 100%;
  height: 320px;
}
</style>
