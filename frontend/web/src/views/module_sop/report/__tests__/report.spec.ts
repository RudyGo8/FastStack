import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Report from "../index.vue";

const { getSpuList, getDimensionOptions, getFirstPhaseReport, getSnapshotList, generateSnapshots } =
  vi.hoisted(() => ({
    getSpuList: vi.fn(),
    getDimensionOptions: vi.fn(),
    getFirstPhaseReport: vi.fn(),
    getSnapshotList: vi.fn(),
    generateSnapshots: vi.fn(),
  }));

vi.mock("@/api/module_sop/data", () => ({ SopDataAPI: { getSpuList } }));
vi.mock("@/api/module_sop/report", () => ({
  SopReportAPI: { getDimensionOptions, getFirstPhaseReport, getSnapshotList, generateSnapshots },
}));
vi.mock("@utils", () => ({ Auth: { getAccessToken: vi.fn(() => "token") } }));

const MOCK_SNAPSHOTS = [
  {
    id: 1,
    spu_code: "C706",
    as_of_date: "2026-09-30",
    report_version: "r1",
    completeness_status: "partial",
    generated_at: "2026-10-01T00:00:00Z",
    record_count: 42,
  },
];

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
    getSpuList.mockResolvedValue({ data: { data: { items: [MOCK_REPORT.spu], total: 1 } } });
    getDimensionOptions.mockResolvedValue({ data: { data: { regions: [], channels: [] } } });
    getFirstPhaseReport.mockResolvedValue({ data: { data: MOCK_REPORT } });
    getSnapshotList.mockResolvedValue({ data: { data: MOCK_SNAPSHOTS } });
    generateSnapshots.mockResolvedValue({ data: { data: { generated_count: 1 } } });
  });

  it("renders the report as a centered document below its toolbar", async () => {
    const wrapper = mount(Report, { global });
    await flushPromises();

    expect(wrapper.find(".sop-report-toolbar").exists()).toBe(true);
    expect(wrapper.find(".sop-report-paper").exists()).toBe(true);
    expect(wrapper.text()).toContain("C706 S&OP 需求走势与分渠道提报预测报告");
    expect(wrapper.text()).toContain("统计口径与规则");
  });

  it("shows metrics, decision summary, and snapshot history in the document", async () => {
    const wrapper = mount(Report, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("核心指标");
    expect(wrapper.text()).toContain("决策摘要");
    expect(wrapper.text()).toContain("S&OP 需求走势");
    expect(wrapper.text()).toContain("部分渠道数据缺失");
    expect(wrapper.text()).toContain("快照历史");
  });

  it("loads the first SPU and supports snapshot generation", async () => {
    const wrapper = mount(Report, { global });
    await flushPromises();

    const generateButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("生成快照"));
    expect(generateButton).toBeDefined();
    await generateButton!.trigger("click");
    await flushPromises();

    expect(generateSnapshots).toHaveBeenCalled();
    expect(getSnapshotList).toHaveBeenCalledTimes(2);
    expect(getFirstPhaseReport).toHaveBeenCalledWith("C706", { region: "" });
  });
});
