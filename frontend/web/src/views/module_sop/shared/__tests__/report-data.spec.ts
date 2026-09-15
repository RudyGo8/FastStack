import { describe, expect, it } from "vitest";

import type { SopFirstPhaseReport } from "@/api/module_sop/types";

import { buildChannelForecastMatrix, buildTrendChartDataset } from "../report-data";

const report: SopFirstPhaseReport = {
  report_version: "v1",
  spu: {
    spu_code: "C706",
    spu_name: "眼镜",
    product_line: "AI",
    brand: "A",
    category: "wearable",
    lifecycle_stage: "growth",
  },
  as_of_date: "2026-09-30",
  filters: { region: "", channel: "" },
  completeness_status: "complete",
  missing_domains: [],
  warnings: [],
  events: [],
  monthly_actuals: [{ period: "2026-08", outbound_qty: 100, activation_qty: 80 }],
  forecasts: [
    {
      forecast_month: "2026-10-01",
      region: "CN",
      channel: "直营渠道",
      forecast_type: "submit",
      forecast_qty: 120,
      version: "v1",
      source_table: "forecast",
      snapshot_at: "2026-09-30",
    },
  ],
  forecast_checks: [
    {
      forecast_month: "2026-10-01",
      region: "CN",
      channel: "直营渠道",
      forecast_qty: 120,
      evaluable: true,
      score: 0.7,
      level: "medium",
      rule_version: "forecast.v1",
      baseline_qty: 100,
      deviation_ratio: 0.2,
      findings: [{ code: "D", severity: "warning", message: "偏差超过 15%" }],
    },
  ],
  provenance: [],
};

describe("S&OP report datasets", () => {
  it("returns empty datasets instead of demo facts", () => {
    expect(buildTrendChartDataset(null)).toEqual([]);
    expect(buildChannelForecastMatrix(null)).toEqual({
      months: [],
      channels: [],
      submitMatrix: {},
      aiBaselineMatrix: {},
      deviationMatrix: {},
      diffList: [],
    });
  });

  it("derives trend and channel differences from the selected report", () => {
    expect(buildTrendChartDataset(report)).toEqual([
      {
        period: "2026-08",
        type: "actual",
        outbound_qty: 100,
        activation_qty: 80,
        ai_forecast_outbound: null,
        ai_forecast_activation: null,
        submit_forecast: null,
        event: "",
      },
      {
        period: "2026-10",
        type: "forecast",
        outbound_qty: null,
        activation_qty: null,
        ai_forecast_outbound: 100,
        ai_forecast_activation: 95,
        submit_forecast: 120,
        event: "",
      },
    ]);
    const matrix = buildChannelForecastMatrix(report);
    expect(matrix.months).toEqual(["2026-10"]);
    expect(matrix.channels).toEqual(["直营渠道"]);
    expect(matrix.submitMatrix["合计"]).toEqual([120]);
    expect(matrix.aiBaselineMatrix["合计"]).toEqual([100]);
    expect(matrix.diffList).toEqual([
      {
        channel: "直营渠道",
        month: "2026-10",
        aiQty: 100,
        submitQty: 120,
        diffQty: 20,
        deviationRatio: 0.2,
        dimension: "渠道能力",
        reason: "偏差超过 15%",
      },
    ]);
  });
});
