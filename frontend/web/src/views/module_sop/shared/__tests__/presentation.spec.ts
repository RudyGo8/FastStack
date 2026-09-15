import { describe, expect, it } from "vitest";

import {
  buildForecastValidationSummary,
  buildKnowledgeMetrics,
  buildSourceContext,
  formatSpuLabel,
  formatOptional,
  getFilePresentation,
} from "../presentation";
import { buildDecisionSummary, buildReportMetrics, getSourceSyncDisplay } from "../report-metrics";

describe("S&OP presentation facts", () => {
  it("keeps missing and zero values distinct", () => {
    expect(formatOptional(null)).toBe("—");
    expect(formatOptional("", " 台")).toBe("—");
    expect(formatOptional(0, " 台")).toBe("0 台");
  });

  it("derives knowledge and validation counts from persisted records", () => {
    expect(
      buildKnowledgeMetrics([
        { filename: "a.pdf", file_type: "pdf", chunk_count: 3 },
        { filename: "b.docx", file_type: "docx", chunk_count: 5 },
      ])
    ).toEqual({
      documentCount: 2,
      chunkCount: 8,
      indexStatus: "索引就绪",
    });
    expect(
      buildForecastValidationSummary([
        { level: "low", evaluable: true },
        { level: "medium", evaluable: true },
        { level: "not_evaluable", evaluable: false },
      ])
    ).toEqual({ total: 3, evaluable: 2, normal: 1, warning: 1, critical: 0, notEvaluable: 1 });
  });

  it("builds source and file labels without inventing facts", () => {
    expect(buildSourceContext({ spu: "C706", region: "", asOfDate: "2026-09-30" })).toBe(
      "SPU：C706 · 区域：全部区域 · 数据来源：企业数据仓库 · 数据截至：2026-09-30"
    );
    expect(getFilePresentation("policy.pdf")).toEqual({
      icon: "document",
      tone: "danger",
      extension: "PDF",
    });
    expect(getSourceSyncDisplay("completed")).toEqual({ label: "同步完成", type: "success" });
  });

  it("does not repeat an SPU code when the source name equals the code", () => {
    expect(formatSpuLabel({ spu_code: "C706", spu_name: "C706" })).toBe("C706");
    expect(formatSpuLabel({ spu_code: "C706", spu_name: "GPS 智能码表" })).toBe(
      "C706 · GPS 智能码表"
    );
  });

  it("distinguishes unsynced core adapters from planned extension domains", () => {
    expect(getSourceSyncDisplay("not_started", "phase_one_core")).toEqual({
      label: "待适配",
      type: "warning",
    });
    expect(getSourceSyncDisplay("not_started", "phase_one_extension")).toEqual({
      label: "扩展域待接入",
      type: "info",
    });
    expect(getSourceSyncDisplay("not_started", "connection_only")).toEqual({
      label: "二期预留",
      type: "info",
    });
  });

  it("does not synthesize report metrics or decisions", () => {
    expect(buildReportMetrics(null)).toEqual({
      totalOutbound: null,
      totalActivation: null,
      activationRate: null,
      forecastAccuracy: null,
      riskCount: 0,
    });
    expect(buildDecisionSummary(null)).toEqual({
      attribution: "暂无可评估的预测校验记录。",
      supply: "暂无出库事实记录。",
      marketing: "暂无终端激活事实记录。",
    });
  });
});
