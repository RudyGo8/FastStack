import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Analysis from "../index.vue";

const { getSpuList, getDimensionOptions, getFirstPhaseReport } = vi.hoisted(() => ({
  getSpuList: vi.fn(),
  getDimensionOptions: vi.fn(),
  getFirstPhaseReport: vi.fn(),
}));

vi.mock("@/api/module_sop/data", () => ({ SopDataAPI: { getSpuList } }));
vi.mock("@/api/module_sop/report", () => ({
  SopReportAPI: { getDimensionOptions, getFirstPhaseReport },
}));
const global = {
  plugins: [ElementPlus],
  stubs: { SopTrendChart: { template: '<div class="trend-chart-stub" />' } },
};

const MOCK_REPORT = {
  report_version: "r1",
  spu: {
    spu_code: "C706",
    spu_name: "AI眼镜",
    product_line: "AR",
    brand: "Test",
    category: "消费",
    lifecycle_stage: "growth",
  },
  as_of_date: "2026-09-30",
  filters: { region: "", channel: "" },
  completeness_status: "partial" as const,
  missing_domains: [],
  warnings: [],
  monthly_actuals: [
    { period: "2026-07", outbound_qty: 100, activation_qty: 80 },
    { period: "2026-08", outbound_qty: 50, activation_qty: 40 },
  ],
  forecasts: [
    {
      forecast_month: "2026-10-01",
      region: "",
      channel: "线上渠道",
      forecast_type: "submit",
      forecast_qty: 120,
      version: "v1",
      source_table: "t",
      snapshot_at: "",
    },
  ],
  forecast_checks: [
    {
      forecast_month: "2026-10-01",
      region: "EU",
      channel: "线上渠道",
      forecast_qty: 120,
      evaluable: true,
      score: 0.8,
      level: "medium",
      rule_version: "forecast.v1",
      baseline_qty: 100,
      deviation_ratio: 0.2,
      findings: [{ code: "HIGH_DEV", severity: "warning", message: "偏差超过 15%" }],
    },
  ],
  provenance: [],
};

describe("S&OP analysis page", () => {
  beforeEach(() => {
    getSpuList.mockResolvedValue({
      data: { data: { items: [{ spu_code: "C706", spu_name: "AI眼镜" }], total: 1 } },
    });
    getDimensionOptions.mockResolvedValue({
      data: { data: { regions: ["EU"], channels: ["线上渠道"] } },
    });
    getFirstPhaseReport.mockResolvedValue({ data: { data: MOCK_REPORT } });
  });

  it("selects the first SPU and loads its analysis automatically", async () => {
    const wrapper = mount(Analysis, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("C706 · AI眼镜");
    expect(getDimensionOptions).toHaveBeenCalledWith("C706");
    expect(getFirstPhaseReport).toHaveBeenCalledWith("C706", { region: "", channel: "" });
  });

  it("shows trend chart, validation summary, channel matrix, and decision summary after report loads", async () => {
    const wrapper = mount(Analysis, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("S&OP 需求走势");
    expect(wrapper.text()).toContain("预测校验");
    expect(wrapper.text()).toContain("分渠道提报预测对比矩阵");
    expect(wrapper.text()).toContain("决策摘要");
    expect(wrapper.text()).toContain("数据血缘");
    expect(wrapper.text()).toContain("归因分析");
  });

  it("preserves zero values instead of showing placeholder", async () => {
    const zeroReport = {
      ...MOCK_REPORT,
      monthly_actuals: [{ period: "2026-07", outbound_qty: 0, activation_qty: 0 }],
    };
    getFirstPhaseReport.mockResolvedValue({ data: { data: zeroReport } });
    const wrapper = mount(Analysis, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("0 台");
  });
});
