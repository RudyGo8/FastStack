import type { SopChannelMatrix, SopFirstPhaseReport, SopTrendPoint } from "@/api/module_sop/types";

const EMPTY_MATRIX: SopChannelMatrix = { months: [], channels: [], submitMatrix: {}, aiBaselineMatrix: {}, deviationMatrix: {}, diffList: [] };

function buildEventMap(report: SopFirstPhaseReport | null): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of report?.events ?? []) {
    const month = String(item.event_month || "").slice(0, 7);
    if (month && item.event) map.set(month, item.event);
  }
  return map;
}

export function buildTrendChartDataset(report: SopFirstPhaseReport | null): SopTrendPoint[] {
  if (!report) return [];
  const eventMap = buildEventMap(report);
  const timeline: SopTrendPoint[] = report.monthly_actuals.map((actual) => ({
    period: actual.period,
    type: "actual",
    outbound_qty: Number(actual.outbound_qty) || 0,
    activation_qty: Number(actual.activation_qty) || 0,
    ai_forecast_outbound: null,
    ai_forecast_activation: null,
    submit_forecast: null,
    event: eventMap.get(actual.period) ?? "",
  }));
  const forecastMap = new Map<string, { submit: number; baseline: number }>();
  for (const check of report.forecast_checks) {
    const month = String(check.forecast_month || "").slice(0, 7);
    if (!month) continue;
    const item = forecastMap.get(month) ?? { submit: 0, baseline: 0 };
    item.submit += Number(check.forecast_qty) || 0;
    if (check.baseline_qty !== null && check.baseline_qty !== undefined) item.baseline = Math.max(item.baseline, Number(check.baseline_qty) || 0);
    forecastMap.set(month, item);
  }
  for (const forecast of report.forecasts) {
    const month = String(forecast.forecast_month || "").slice(0, 7);
    if (!month) continue;
    const item = forecastMap.get(month) ?? { submit: 0, baseline: 0 };
    if (!report.forecast_checks.length) item.submit += Number(forecast.forecast_qty) || 0;
    forecastMap.set(month, item);
  }
  for (const month of [...forecastMap.keys()].sort()) {
    const item = forecastMap.get(month)!;
    const baseline = item.baseline > 0 ? Math.round(item.baseline) : null;
    timeline.push({ period: month, type: "forecast", outbound_qty: null, activation_qty: null, ai_forecast_outbound: baseline, ai_forecast_activation: baseline ? Math.round(baseline * 0.95) : null, submit_forecast: Math.round(item.submit), event: eventMap.get(month) ?? "" });
  }
  return timeline;
}

export function buildChannelForecastMatrix(report: SopFirstPhaseReport | null): SopChannelMatrix {
  if (!report) return { ...EMPTY_MATRIX };
  const months = [...new Set([...report.forecast_checks.map((item) => item.forecast_month.slice(0, 7)), ...report.forecasts.map((item) => item.forecast_month.slice(0, 7))].filter(Boolean))].sort().slice(0, 6);
  const channels = [...new Set([...report.forecast_checks.map((item) => item.channel), ...report.forecasts.map((item) => item.channel)].filter(Boolean))].sort();
  if (!months.length || !channels.length) return { ...EMPTY_MATRIX };
  const matrix: SopChannelMatrix = { months, channels, submitMatrix: {}, aiBaselineMatrix: {}, deviationMatrix: {}, diffList: [] };
  for (const channel of channels) {
    matrix.submitMatrix[channel] = [];
    matrix.aiBaselineMatrix[channel] = [];
    matrix.deviationMatrix[channel] = [];
    for (const month of months) {
      const check = report.forecast_checks.find((item) => item.channel === channel && item.forecast_month.slice(0, 7) === month);
      const forecast = report.forecasts.find((item) => item.channel === channel && item.forecast_month.slice(0, 7) === month);
      const submit = Number(check?.forecast_qty ?? forecast?.forecast_qty ?? 0) || 0;
      const aiQty = check?.baseline_qty === null || check?.baseline_qty === undefined ? 0 : Math.round(Number(check.baseline_qty) || 0);
      const deviationRatio = check?.deviation_ratio === null || check?.deviation_ratio === undefined ? (aiQty > 0 ? (submit - aiQty) / aiQty : 0) : Number(check.deviation_ratio);
      matrix.submitMatrix[channel].push(submit);
      matrix.aiBaselineMatrix[channel].push(aiQty);
      matrix.deviationMatrix[channel].push(deviationRatio);
      if (aiQty > 0 && Math.abs(deviationRatio) > 0.05) {
        let dimension = "促销/季节性";
        if (channel.includes("海外")) dimension = "库存与周转";
        else if (channel.includes("渠道") || channel.includes("门店")) dimension = "渠道能力";
        else if (channel.includes("运营商") || channel.includes("行业")) dimension = "客户订单/项目";
        matrix.diffList.push({ channel, month, aiQty, submitQty: submit, diffQty: submit - aiQty, deviationRatio, dimension, reason: check?.findings.map((item) => item.message).filter(Boolean).join("；") || `预测偏离基准 ${(deviationRatio * 100).toFixed(1)}%` });
      }
    }
  }
  const submitTotals = months.map((_, index) => channels.reduce((sum, channel) => sum + (matrix.submitMatrix[channel]?.[index] ?? 0), 0));
  const baselineTotals = months.map((_, index) => channels.reduce((sum, channel) => sum + (matrix.aiBaselineMatrix[channel]?.[index] ?? 0), 0));
  matrix.submitMatrix["合计"] = submitTotals;
  matrix.aiBaselineMatrix["合计"] = baselineTotals;
  matrix.deviationMatrix["合计"] = months.map((_, index) => {
    const baseline = baselineTotals[index] ?? 0;
    const submitted = submitTotals[index] ?? 0;
    return baseline > 0 ? (submitted - baseline) / baseline : 0;
  });
  matrix.diffList.sort((a, b) => Math.abs(b.deviationRatio) - Math.abs(a.deviationRatio));
  return matrix;
}
