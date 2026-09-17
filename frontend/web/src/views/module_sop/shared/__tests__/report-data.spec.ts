import { describe, expect, it } from "vitest";

import type { SopFirstPhaseReport } from "@/api/module_sop/types";

import {
  buildAnnualChannelMatrix,
  buildChannelForecastMatrix,
  buildTrendChartDataset,
} from "../report-data";

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
  channel_actuals: [],
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
  it("adds all other channels and keeps current-month document actuals visible", () => {
    const actual = (channel: string, outbound_qty: number, activation_qty: number) => ({
      period: "2026-09",
      region: "全球",
      channel,
      outbound_qty,
      activation_qty,
    });
    const forecast = (channel: string, forecast_qty: number) => ({
      ...report.forecasts[0]!,
      forecast_month: "2026-10-01",
      snapshot_at: "2026-09-15T00:00:00",
      region: "全球",
      channel,
      forecast_qty,
    });
    const matrix = buildAnnualChannelMatrix({
      ...report,
      as_of_date: "2026-09-16",
      channel_actuals: [
        actual("大客户解决方案部", 10, 2),
        actual("未归属渠道", 20, 3),
        actual("其他", 4, 1),
        actual("海外渠道销售一部", 50, 8),
      ],
      forecasts: [forecast("跨境", 100), forecast("国际品牌营销部", 200)],
    });
    expect(matrix.rows.map((r) => r.channel)).toEqual([
      "国际渠道销售一部",
      "国际渠道销售二部",
      "海外电商",
      "国内渠道",
      "国内电商",
      "其他",
    ]);
    const other = matrix.rows.find((r) => r.channel === "其他")!;
    expect(other.outboundOrForecast[8]).toBe(34);
    expect(other.activations[8]).toBe(6);
    expect(other.outboundOrForecast[10]).toBe(300);
    expect(matrix.rows[0]!.outboundOrForecast[8]).toBe(50);
  });
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

  it("derives submitted forecasts without inventing unavailable AI baselines", () => {
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
        ai_forecast_outbound: null,
        ai_forecast_activation: null,
        submit_forecast: 120,
        event: "",
      },
    ]);
    const matrix = buildChannelForecastMatrix(report);
    expect(matrix.months).toEqual(["2026-10"]);
    expect(matrix.channels).toEqual(["直营渠道"]);
    expect(matrix.submitMatrix["合计"]).toEqual([120]);
    expect(matrix.aiBaselineMatrix).toEqual({});
    expect(matrix.deviationMatrix).toEqual({});
    expect(matrix.diffList).toEqual([]);
  });

  it("places actuals and only the latest submitted forecast in exact annual cells", () => {
    const annual = buildAnnualChannelMatrix({
      ...report,
      as_of_date: "2026-09-16",
      channel_actuals: [
        {
          period: "2026-08",
          region: "CN-North",
          channel: "国内渠道",
          outbound_qty: 2000,
          activation_qty: 1400,
        },
        {
          period: "2026-08",
          region: "CN-South",
          channel: "国内渠道",
          outbound_qty: 104,
          activation_qty: 87,
        },
        {
          period: "2026-08",
          region: "CN-South",
          channel: "其他",
          outbound_qty: 9,
          activation_qty: 4,
        },
        {
          period: "2026-08",
          region: "CN",
          channel: "国际渠道销售一部",
          outbound_qty: 640,
          activation_qty: 510,
        },
      ],
      forecasts: [
        {
          ...report.forecasts[0]!,
          region: "CN",
          channel: "国内渠道",
          forecast_month: "2026-10-01",
          forecast_qty: 120,
          version: "v1",
          snapshot_at: "2026-08-31T00:00:00",
        },
        {
          ...report.forecasts[0]!,
          region: "CN",
          channel: "国内渠道",
          forecast_month: "2026-10-01",
          forecast_qty: 1500,
          version: "v2",
          snapshot_at: "2026-09-16T00:00:00",
        },
        {
          ...report.forecasts[0]!,
          region: "CN",
          channel: "国内渠道",
          forecast_month: "2026-10-01",
          forecast_qty: 1800,
          version: "v3",
          snapshot_at: "2026-09-17T00:00:00",
        },
        {
          ...report.forecasts[0]!,
          region: "CN",
          channel: "国内渠道",
          forecast_month: "2026-10-01",
          forecast_type: "ai_baseline",
          forecast_qty: 999,
          version: "ai-v1",
          snapshot_at: "2026-09-17T00:00:00",
        },
      ],
    });

    expect(annual.year).toBe(2026);
    expect(annual.salesMonthCount).toBe(9);
    expect(annual.months).toHaveLength(15);
    expect(annual.rows).toHaveLength(6);
    // 实际区包含当前月；预测区单独包含当前月起六个月。
    const domesticRow = annual.rows.find((r) => r.channel === "国内渠道");
    expect(domesticRow).toBeDefined();
    expect(domesticRow!.outboundOrForecast[7]).toBe(2104); // 8月销售
    expect(domesticRow!.outboundOrForecast[8]).toBeNull(); // 9月无真实出库，不以预测补齐
    expect(domesticRow!.outboundOrForecast[10]).toBe(1500); // 预测区10月
    expect(domesticRow!.activations[7]).toBe(1487); // 8月激活
    // 数仓渠道名（国际渠道销售一部/二部）必须独立成行，不能被并入"其他"
    const overseasRow = annual.rows.find((r) => r.channel === "国际渠道销售一部");
    expect(overseasRow).toBeDefined();
    expect(overseasRow!.outboundOrForecast[7]).toBe(640);
    expect(overseasRow!.activations[7]).toBe(510);
    const otherRow = annual.rows.find((r) => r.channel === "其他")!;
    expect(otherRow.outboundOrForecast[7]).toBe(9);
  });

  it("does not invent channel allocation for aggregate-only legacy snapshots", () => {
    const annual = buildAnnualChannelMatrix({
      ...report,
      channel_actuals: [],
      forecasts: [],
    });

    expect(annual.rows).toHaveLength(6);
    expect(
      annual.rows.every((row) => row.outboundOrForecast.every((value) => value === null))
    ).toBe(true);
    expect(annual.rows.every((row) => row.activations.every((value) => value === null))).toBe(true);
  });
  it("keeps actual and forecast September in separate report 2 groups with the same six-month total", () => {
    const forecasts = Array.from({ length: 7 }, (_, i) => ({
      ...report.forecasts[0]!,
      forecast_month:
        i < 4
          ? `2026-${String(i + 9).padStart(2, "0")}-01`
          : `2027-${String(i - 3).padStart(2, "0")}-01`,
      forecast_qty: 100.5,
      channel: "国内渠道",
      snapshot_at: "2026-09-17",
    }));
    const source = {
      ...report,
      as_of_date: "2026-09-30",
      monthly_actuals: [{ period: "2026-09", outbound_qty: 10, activation_qty: 9 }],
      channel_actuals: [
        {
          period: "2026-09",
          region: "CN",
          channel: "国内渠道",
          outbound_qty: 10,
          activation_qty: 9,
        },
      ],
      forecasts,
    };
    const matrix = buildAnnualChannelMatrix(source);
    expect(matrix.months.slice(matrix.salesMonthCount)).toEqual([
      "2026-09",
      "2026-10",
      "2026-11",
      "2026-12",
      "2027-01",
      "2027-02",
    ]);
    expect(
      matrix.rows
        .find((x) => x.channel === "国内渠道")!
        .outboundOrForecast.slice(matrix.salesMonthCount)
    ).toEqual(Array(6).fill(100.5));
    const trend = buildTrendChartDataset(source);
    expect(trend.filter((x) => x.period === "2026-09")).toHaveLength(1);
    expect(trend.find((x) => x.period === "2026-09")).toMatchObject({
      outbound_qty: 10,
      activation_qty: 9,
      submit_forecast: 100.5,
    });
    expect(trend.reduce((s, x) => s + (x.submit_forecast ?? 0), 0)).toBe(603);
  });
});
