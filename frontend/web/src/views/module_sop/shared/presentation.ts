import type { SopDocumentInfo, SopForecastCheck, SopSpuInfo } from "@/api/module_sop/types";

type ValidationLike = Pick<SopForecastCheck, "level" | "evaluable">;

export function formatOptional(value: unknown, unit = ""): string {
  if (value === null || value === undefined || value === "") return "—";
  return `${String(value)}${unit}`;
}

export function formatSpuLabel(spu: Pick<SopSpuInfo, "spu_code" | "spu_name">): string {
  const code = spu.spu_code.trim();
  const name = spu.spu_name.trim();
  if (!name || name.toLocaleLowerCase() === code.toLocaleLowerCase()) return code;
  return `${code} · ${name}`;
}

export function buildKnowledgeMetrics(documents: SopDocumentInfo[] = []) {
  const chunkCount = documents.reduce(
    (sum, document) => sum + (Number(document.chunk_count) || 0),
    0
  );
  return {
    documentCount: documents.length,
    chunkCount,
    indexStatus: documents.length ? "索引就绪" : "暂无文档",
  };
}

export function buildForecastValidationSummary(checks: ValidationLike[] = []) {
  return {
    total: checks.length,
    evaluable: checks.filter((item) => item.evaluable !== false).length,
    normal: checks.filter((item) => item.level === "low").length,
    warning: checks.filter((item) => item.level === "medium").length,
    critical: checks.filter((item) => item.level === "high").length,
    notEvaluable: checks.filter((item) => item.evaluable === false).length,
  };
}

export function buildSourceContext({
  spu,
  region,
  asOfDate,
}: {
  spu?: string;
  region?: string;
  asOfDate?: string;
}): string {
  return [
    `SPU：${spu || "—"}`,
    `区域：${region || "全部区域"}`,
    "数据来源：企业数据仓库",
    `数据截至：${asOfDate || "—"}`,
  ].join(" · ");
}

export function buildForecastValidationRows(checks: SopForecastCheck[] = []) {
  return checks.map((check) => ({
    month: String(check.forecast_month || "").slice(0, 7) || "—",
    scope: `${check.region || "全部区域"} / ${check.channel || "全部渠道"}`,
    forecastQty: check.forecast_qty,
    baselineQty: check.baseline_qty,
    deviationRatio: check.deviation_ratio,
    evaluable: check.evaluable !== false,
    level: check.level,
    ruleVersion: check.rule_version || "—",
    findingText:
      (check.findings || [])
        .map((item) => item.message)
        .filter(Boolean)
        .join("；") || "未命中异常规则",
  }));
}

export function getFilePresentation(filename = "") {
  const extension = filename.split(".").pop()?.toUpperCase() || "FILE";
  if (extension === "PDF") return { icon: "document", tone: "danger", extension };
  if (["DOC", "DOCX"].includes(extension)) return { icon: "document", tone: "primary", extension };
  if (["XLS", "XLSX"].includes(extension)) return { icon: "tickets", tone: "success", extension };
  if (["MD", "TXT"].includes(extension)) return { icon: "document", tone: "info", extension };
  if (["PNG", "JPG", "JPEG", "WEBP"].includes(extension))
    return { icon: "picture", tone: "warning", extension };
  return { icon: "document", tone: "info", extension };
}
