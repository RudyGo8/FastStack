import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Dashboard from "../index.vue";

const {
  getDataStatus,
  getSpuList,
  listDocuments,
  getSnapshotList,
  getFirstPhaseReport,
  getDimensionOptions,
} = vi.hoisted(() => ({
  getDataStatus: vi.fn(),
  getSpuList: vi.fn(),
  listDocuments: vi.fn(),
  getSnapshotList: vi.fn(),
  getFirstPhaseReport: vi.fn(),
  getDimensionOptions: vi.fn(),
}));

vi.mock("@/api/module_sop/data", () => ({ SopDataAPI: { getDataStatus, getSpuList } }));
vi.mock("@/api/module_ai/document", () => ({ SopDocumentAPI: { list: listDocuments } }));
vi.mock("@/api/module_sop/report", () => ({
  SopReportAPI: { getSnapshotList, getFirstPhaseReport, getDimensionOptions },
}));
const global = {
  plugins: [ElementPlus],
  stubs: { SopTrendChart: { template: '<div class="trend-chart-stub" />' } },
};

describe("S&OP 计划工作台", () => {
  beforeEach(() => {
    getSpuList.mockResolvedValue({
      data: { data: { items: [{ spu_code: "C706", spu_name: "AI眼镜" }], total: 1 } },
    });
    getFirstPhaseReport.mockResolvedValue({ data: { data: null } });
    getDimensionOptions.mockResolvedValue({ data: { data: { regions: [], channels: [] } } });
  });

  it("renders SPU, region, period, channel, and refresh controls", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("C706 · AI眼镜");
    expect(wrapper.text()).toContain("全部区域");
    expect(wrapper.text()).toContain("周期");
    expect(wrapper.text()).toContain("全部渠道");
    expect(wrapper.text()).toContain("数据时点");
    expect(wrapper.text()).toContain("刷新数据");
    expect(wrapper.text()).toContain("查看完整会议报告");
  });

  it("renders the four KPIs backed by current business data", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("管理中的 SPU");
    expect(wrapper.text()).toContain("历史累计出库");
    expect(wrapper.text()).toContain("累计终端激活");
    expect(wrapper.text()).toContain("未来6个月提报总量");
    expect(wrapper.findAll(".kpi-card")).toHaveLength(4);
  });

  it("renders trend chart and channel matrix sections when report loads", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("历史出库/激活与未来6个月提报预测");
    expect(wrapper.text()).toContain("分渠道销售、激活与提报预测");
  });

  it("renders report 2 as a current-year sales and forecast matrix", async () => {
    getFirstPhaseReport.mockResolvedValue({
      data: {
        data: {
          report_version: "v1",
          spu: {
            spu_code: "C706",
            spu_name: "AI眼镜",
            product_line: "AI",
            brand: "A",
            category: "wearable",
            lifecycle_stage: "growth",
          },
          as_of_date: "2026-09-16",
          filters: { region: "", channel: "" },
          completeness_status: "complete",
          missing_domains: [],
          warnings: [],
          events: [],
          monthly_actuals: [{ period: "2026-08", outbound_qty: 3089, activation_qty: 2131 }],
          channel_actuals: [
            {
              period: "2026-08",
              region: "国内",
              channel: "国内渠道",
              outbound_qty: 2104,
              activation_qty: 1487,
            },
            {
              period: "2026-08",
              region: "海外",
              channel: "海外电商",
              outbound_qty: 985,
              activation_qty: 644,
            },
          ],
          forecasts: [
            {
              forecast_month: "2026-10-01",
              region: "国内",
              channel: "国内渠道",
              forecast_type: "submit",
              forecast_qty: 1500,
              version: "v1",
              source_table: "forecast",
              snapshot_at: "2026-09-16T00:00:00",
            },
            {
              forecast_month: "2026-12-01",
              region: "海外",
              channel: "海外电商",
              forecast_type: "submit",
              forecast_qty: 1180,
              version: "v1",
              source_table: "forecast",
              snapshot_at: "2026-09-16T00:00:00",
            },
          ],
          forecast_checks: [],
          provenance: [],
        },
      },
    });

    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    const table = wrapper.get(".annual-channel-table");
    expect(table.get(".group-sales").attributes("colspan")).toBe("6");
    expect(table.get(".group-forecast").attributes("colspan")).toBe("6");
    expect(table.text()).toContain("2026年4月");
    expect(table.text()).toContain("2026年12月");
    expect(table.text()).toContain("国内渠道");
    expect(table.text()).toContain("海外电商");
    expect(table.text()).toContain("出库/预测");
    expect(table.text()).toContain("激活");
    expect(table.text()).toContain("2104");
    expect(table.text()).toContain("1487");
    expect(table.text()).toContain("1500");
    expect(table.findAll('tbody th[rowspan="2"]')).toHaveLength(6);
  });

  it("automatically opens the first available SPU", async () => {
    mount(Dashboard, { global });
    await flushPromises();

    expect(getDimensionOptions).toHaveBeenCalledWith("C706");
    expect(getFirstPhaseReport).toHaveBeenCalledWith(
      "C706",
      expect.objectContaining({ region: "", channel: "" })
    );
  });

  it("does not present unavailable AI baselines as real business data", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).not.toContain("AI 基线预测");
    expect(wrapper.text()).not.toContain("AI 基线预测");
    expect(wrapper.text()).not.toContain("差异明细与原因归因");
  });
  it("loads every managed SPU without a default C search or a twenty-item cutoff", async () => {
    const items = Array.from({ length: 31 }, (_, index) => ({
      spu_code: index === 0 ? "AT1200" : index === 1 ? "C416" : `P${index}`,
      spu_name: `Product ${index}`,
    }));
    getSpuList.mockImplementation(async (params) => ({
      data: {
        data: {
          items: params.search
            ? items.filter((x) => x.spu_code.includes(params.search)).slice(0, params.limit)
            : items.slice(0, params.limit),
          total: params.search
            ? items.filter((x) => x.spu_code.includes(params.search)).length
            : items.length,
        },
      },
    }));
    const wrapper = mount(Dashboard, { global });
    await flushPromises();
    const vm = wrapper.vm as any;
    expect(vm.spuOptions).toHaveLength(31);
    expect(vm.spuOptions.map((x: any) => x.spu_code)).toContain("AT1200");
    expect(vm.spuTotal).toBe(31);
    wrapper.unmount();
  });

  it("clearing SPU search restores the complete list and preserves the current selection", async () => {
    const items = [
      { spu_code: "C416", spu_name: "C416" },
      { spu_code: "AT1200", spu_name: "AT1200" },
    ];
    getSpuList.mockImplementation(async (params) => ({
      data: {
        data: {
          items: items.filter((x) => !params.search || x.spu_code.includes(params.search)),
          total: items.length,
        },
      },
    }));
    const wrapper = mount(Dashboard, { global });
    await flushPromises();
    const vm = wrapper.vm as any;
    vm.spuCode = "C416";
    await vm.searchSpus("AT1200");
    expect(vm.spuOptions).toHaveLength(1);
    await vm.searchSpus("");
    expect(vm.spuOptions).toHaveLength(2);
    expect(vm.spuCode).toBe("C416");
    wrapper.unmount();
  });
});
