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

  it("renders SPU selector, region selector, period picker, and refresh button", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("C706 · AI眼镜");
    expect(wrapper.text()).toContain("全部区域");
    expect(wrapper.text()).toContain("计划周期");
    expect(wrapper.text()).toContain("数据时点");
    expect(wrapper.text()).toContain("刷新数据");
    expect(wrapper.text()).toContain("查看完整会议报告");
  });

  it("renders 5 KPI cards with correct labels", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("管理中的 SPU");
    expect(wrapper.text()).toContain("历史累计出库");
    expect(wrapper.text()).toContain("累计终端激活");
    expect(wrapper.text()).toContain("未来6个月提报总量");
    expect(wrapper.text()).toContain("预测差异项");
  });

  it("renders trend chart and channel matrix sections when report loads", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("S&OP 需求走势");
    expect(wrapper.text()).toContain("分渠道提报预测对比矩阵");
  });

  it("automatically opens the first available SPU", async () => {
    mount(Dashboard, { global });
    await flushPromises();

    expect(getDimensionOptions).toHaveBeenCalledWith("C706");
    expect(getFirstPhaseReport).toHaveBeenCalledWith("C706", { region: "" });
  });

  it("renders variance attribution and rule guidance beside the reports", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();

    expect(wrapper.text()).toContain("差异明细与原因归因");
    expect(wrapper.text()).toContain("S&OP 规则校验与协同概述");
    expect(wrapper.find(".sop-insight-grid").exists()).toBe(true);
  });
});
