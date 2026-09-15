import type { SopFirstPhaseReport } from "@/api/module_sop/types";

import { buildForecastValidationSummary } from "./presentation";

const SOURCE_SYNC_STATUS = {
  completed: { label: "同步完成", type: "success" },
  partial: { label: "部分成功", type: "warning" },
  failed: { label: "同步失败", type: "danger" },
  not_started: { label: "未同步", type: "info" },
} as const;

const REPORT_READINESS_STATUS = {
  complete: { label: "核心数据域已就绪", banner: "核心数据已就绪 · 可评审", type: "success" },
  partial: { label: "部分数据域已就绪", banner: "数据域不完整 · 待补充", type: "warning" },
  not_ready: { label: "核心数据域未就绪", banner: "核心数据未就绪 · 暂不可评审", type: "danger" },
} as const;

function finiteNumber(value: unknown): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

export function getSourceSyncDisplay(status: string, phaseScope = "") {
  if (status === "not_started") {
    if (phaseScope === "phase_one_extension")
      return { label: "扩展域待接入", type: "info" as const };
    if (phaseScope === "connection_only") return { label: "二期预留", type: "info" as const };
    return { label: "待适配", type: "warning" as const };
  }
  return (
    SOURCE_SYNC_STATUS[status as keyof typeof SOURCE_SYNC_STATUS] ?? {
      label: "状态未知",
      type: "info" as const,
    }
  );
}

export function getReportReadinessDisplay(status: string) {
  return (
    REPORT_READINESS_STATUS[status as keyof typeof REPORT_READINESS_STATUS] ??
    REPORT_READINESS_STATUS.not_ready
  );
}

export function getOverallDataStatusDisplay(status: string, hasError = false) {
  if (hasError) return { label: "数据服务异常", type: "danger" as const };
  const values = {
    ready: { label: "生产数仓 · 核心数据已就绪", type: "success" as const },
    partial: { label: "部分数据域已就绪", type: "warning" as const },
    not_started: { label: "业务数据待接入", type: "warning" as const },
  };
  return (
    values[status as keyof typeof values] ?? { label: "数据状态未知", type: "warning" as const }
  );
}

export function buildReportMetrics(report: SopFirstPhaseReport | null) {
  if (!report)
    return {
      totalOutbound: null,
      totalActivation: null,
      activationRate: null,
      forecastAccuracy: null,
      riskCount: 0,
    };
  const totalOutbound = report.monthly_actuals.reduce(
    (sum, item) => sum + finiteNumber(item.outbound_qty),
    0
  );
  const totalActivation = report.monthly_actuals.reduce(
    (sum, item) => sum + finiteNumber(item.activation_qty),
    0
  );
  const evaluable = report.forecast_checks.filter(
    (item) => item.evaluable !== false && Number.isFinite(Number(item.deviation_ratio))
  );
  const forecastAccuracy = evaluable.length
    ? evaluable.reduce(
        (sum, item) => sum + Math.max(0, 1 - Math.abs(Number(item.deviation_ratio))),
        0
      ) / evaluable.length
    : null;
  return {
    totalOutbound,
    totalActivation,
    activationRate: totalOutbound > 0 ? totalActivation / totalOutbound : null,
    forecastAccuracy,
    riskCount: report.forecast_checks.filter((item) => ["high", "medium"].includes(item.level))
      .length,
  };
}

export function buildMaterialList(report: SopFirstPhaseReport | null) {
  if (!report?.spu?.spu_code) return [];
  const readiness = getReportReadinessDisplay(report.completeness_status);
  return [
    {
      name: `${report.spu.spu_code} 产销决策简报`,
      type: "S&OP 标准报告",
      version: report.report_version || "—",
      time: report.as_of_date || "—",
      status: readiness.label,
      tagType: readiness.type,
    },
  ];
}

export function buildDecisionSummary(report: SopFirstPhaseReport | null) {
  if (!report)
    return {
      attribution: "暂无可评估的预测校验记录。",
      supply: "暂无出库事实记录。",
      marketing: "暂无终端激活事实记录。",
    };
  const validation = buildForecastValidationSummary(report.forecast_checks);
  const totalOutbound = report.monthly_actuals.reduce(
    (sum, item) => sum + finiteNumber(item.outbound_qty),
    0
  );
  const totalActivation = report.monthly_actuals.reduce(
    (sum, item) => sum + finiteNumber(item.activation_qty),
    0
  );
  return {
    attribution: validation.total
      ? `本期共核验 ${validation.total} 项预测：正常 ${validation.normal} 项、关注 ${validation.warning} 项、重点偏离 ${validation.critical} 项、暂不可评估 ${validation.notEvaluable} 项。`
      : "暂无可评估的预测校验记录。",
    supply: report.monthly_actuals.length
      ? `统计区间累计出库 ${totalOutbound.toLocaleString()} 台。`
      : "暂无出库事实记录。",
    marketing: report.monthly_actuals.length
      ? `统计区间累计终端激活 ${totalActivation.toLocaleString()} 台。`
      : "暂无终端激活事实记录。",
  };
}
