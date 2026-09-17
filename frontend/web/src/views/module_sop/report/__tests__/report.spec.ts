import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Report from "../index.vue";

const mockRoute = vi.hoisted(() => ({ query: {} }));
vi.mock("vue-router", async () => {
  const actual = await vi.importActual<any>("vue-router");
  return {
    ...actual,
    useRoute: () => mockRoute,
  };
});

const { getSpuList, getDimensionOptions, getFirstPhaseReport } = vi.hoisted(() => ({
  getSpuList: vi.fn(),
  getDimensionOptions: vi.fn(),
  getFirstPhaseReport: vi.fn(),
}));

vi.mock("@/api/module_sop/data", () => ({ SopDataAPI: { getSpuList } }));
vi.mock("@/api/module_sop/report", () => ({
  SopReportAPI: { getDimensionOptions, getFirstPhaseReport },
}));
vi.mock("@utils", () => ({ Auth: { getAccessToken: vi.fn(() => "token") } }));

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
  warnings: ["部分渠道数据缺失"],
  monthly_actuals: [{ period: "2026-07", outbound_qty: 100, activation_qty: 80 }],
  events: [],
  forecasts: [],
  forecast_checks: [],
  provenance: [],
};

const global = {
  plugins: [ElementPlus],
  stubs: { SopTrendChart: { template: '<div class="trend-chart-stub" />' } },
};

describe("S&OP report page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRoute.query = {};
    getSpuList.mockResolvedValue({ data: { data: { items: [MOCK_REPORT.spu], total: 1 } } });
    getDimensionOptions.mockResolvedValue({ data: { data: { regions: [], channels: [] } } });
    getFirstPhaseReport.mockResolvedValue({ data: { data: MOCK_REPORT } });
  });

  it("renders the report as a centered document below its toolbar", async () => {
    const wrapper = mount(Report, { global });
    await flushPromises();

    expect(wrapper.find(".sop-report-toolbar").exists()).toBe(true);
    expect(wrapper.find(".sop-report-paper").exists()).toBe(true);
    expect(wrapper.text()).toContain("C706 S&OP 需求走势与分渠道提报预测报告");
    expect(wrapper.text()).toContain("实际出库（按单据日期）");
  });

  it("shows metrics, decision summary in the document", async () => {
    const wrapper = mount(Report, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("核心指标");
    expect(wrapper.text()).toContain("决策摘要");
    expect(wrapper.text()).toContain("历史出库/激活与未来6个月提报预测");
    expect(wrapper.text()).toContain("部分渠道数据缺失");
  });

  it("no longer renders snapshot history or generate button", async () => {
    const wrapper = mount(Report, { global });
    await flushPromises();

    expect(wrapper.text()).not.toContain("快照历史");
    expect(wrapper.text()).not.toContain("生成快照");
  });

  it("passes region and channel when preset from route query", async () => {
    mockRoute.query = {
      spu: "C706",
      region: "国内",
      channel: "国内电商",
      start: "2026-04",
      end: "2026-09",
    };
    getFirstPhaseReport.mockResolvedValue({ data: { data: { ...MOCK_REPORT } } });
    const wrapper = mount(Report, { global });
    await flushPromises();
    expect(getFirstPhaseReport).toHaveBeenCalledWith("C706", {
      region: "国内",
      channel: "国内电商",
      start_month: "2026-04",
      end_month: "2026-09",
    });
    expect(wrapper.text()).toContain("区域: 国内");
    expect(wrapper.text()).toContain("渠道: 国内电商");
    expect(wrapper.text()).toContain("2026-04");
    mockRoute.query = {};
  });

  it("no longer renders the removed Excel export button", async () => {
    const wrapper = mount(Report, { global });
    await flushPromises();
    expect(wrapper.text()).not.toContain("导出 Excel");
  });
});
