import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard from "../index.vue";
import { defineComponent, h, KeepAlive, ref } from "vue";
const { getSpuList, refreshData, getFirstPhaseReport, getDimensionOptions } = vi.hoisted(() => ({
  getSpuList: vi.fn(),
  refreshData: vi.fn(),
  getFirstPhaseReport: vi.fn(),
  getDimensionOptions: vi.fn(),
}));
vi.mock("@/api/module_sop/data", () => ({ SopDataAPI: { getSpuList } }));
vi.mock("@/api/module_sop/report", () => ({
  SopReportAPI: { getFirstPhaseReport, getDimensionOptions, refreshData },
}));
const global = { plugins: [ElementPlus], stubs: { SopTrendChart: { template: "<div />" } } };
function report(qty = 100) {
  return {
    report_version: "audit",
    spu: {
      spu_code: "C416",
      spu_name: "C416",
      product_line: "",
      brand: "",
      category: "",
      lifecycle_stage: "",
    },
    as_of_date: "2026-09-17",
    filters: { region: "", channel: "" },
    completeness_status: "complete",
    missing_domains: [],
    warnings: [],
    events: [],
    monthly_actuals: [
      { period: "2026-04", outbound_qty: qty, activation_qty: qty },
      { period: "2026-05", outbound_qty: qty, activation_qty: qty },
      { period: "2026-09", outbound_qty: qty, activation_qty: qty },
    ],
    channel_actuals: [],
    forecasts: [],
    forecast_checks: [],
    provenance: [],
  };
}
const response = (qty: number) => ({ data: { data: report(qty) } });
describe("工作台筛选真实性审计：筛选回归", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    refreshData.mockResolvedValue({ data: { details: { snapshot_status: "ready" } } });
    getSpuList.mockResolvedValue({ data: { data: { items: [report().spu], total: 31 } } });
    getDimensionOptions.mockResolvedValue({
      data: { data: { regions: ["全球"], channels: ["国内渠道", "国内电商"] } },
    });
    getFirstPhaseReport.mockResolvedValue(response(100));
  });
  it("较早渠道请求迟到时应保持最新筛选结果", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();
    const vm = wrapper.vm as any;
    let resolveOld: any, resolveNew: any;
    getFirstPhaseReport
      .mockReturnValueOnce(new Promise((r) => (resolveOld = r)))
      .mockReturnValueOnce(new Promise((r) => (resolveNew = r)));
    vm.channel = "国内渠道";
    const old = vm.loadReport();
    vm.channel = "国内电商";
    const latest = vm.loadReport();
    resolveNew(response(200));
    await latest;
    await flushPromises();
    expect(vm.report.monthly_actuals[0].outbound_qty).toBe(200);
    resolveOld(response(50));
    await old;
    await flushPromises();
    const qty = vm.report.monthly_actuals[0].outbound_qty;
    wrapper.unmount();
    expect(qty).toBe(200);
  });
  it("历史走势图应遵守所选结束月份", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();
    const vm = wrapper.vm as any;
    vm.dateRange = ["2026-04", "2026-05"];
    await flushPromises();
    const months = vm.trendData.filter((x: any) => x.type === "actual").map((x: any) => x.period);
    wrapper.unmount();
    expect(months).toEqual(["2026-04", "2026-05"]);
  });
  it("新筛选加载失败时不应显示上一次筛选的数据", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();
    const vm = wrapper.vm as any;
    getFirstPhaseReport.mockRejectedValueOnce(new Error("audit timeout"));
    vm.channel = "其他";
    await vm.loadReport().catch(() => {});
    await flushPromises();
    const stale = vm.report;
    wrapper.unmount();
    expect(stale).toBeNull();
  });
  it("按所选历史月份向后端请求完整事实", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();
    const vm = wrapper.vm as any;
    vm.dateRange = ["2024-01", "2024-12"];
    await vm.loadReport();
    expect(getFirstPhaseReport).toHaveBeenLastCalledWith(
      "C416",
      expect.objectContaining({ start_month: "2024-01", end_month: "2024-12" })
    );
    wrapper.unmount();
  });
  it("刷新先同步数仓，完成后重新请求当前筛选", async () => {
    const wrapper = mount(Dashboard, { global });
    await flushPromises();
    getFirstPhaseReport.mockClear();
    let finish: any;
    refreshData.mockReturnValueOnce(new Promise((r) => (finish = r)));
    await wrapper
      .findAll("button")
      .find((x) => x.text().includes("刷新数据"))!
      .trigger("click");
    await flushPromises();
    expect(refreshData).toHaveBeenCalledTimes(1);
    expect(getFirstPhaseReport).not.toHaveBeenCalled();
    finish({ data: { details: { snapshot_status: "ready" } } });
    await flushPromises();
    expect(getFirstPhaseReport).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
  it("返回保留的工作台页面时重新加载已更新的事实", async () => {
    const visible = ref(true);
    const Host = defineComponent(
      () => () => h(KeepAlive, {}, { default: () => (visible.value ? h(Dashboard) : null) })
    );
    const wrapper = mount(Host, { global });
    await flushPromises();
    visible.value = false;
    await flushPromises();
    getFirstPhaseReport.mockResolvedValueOnce(response(200));
    visible.value = true;
    await flushPromises();
    expect(
      (wrapper.findComponent(Dashboard).vm as any).report.monthly_actuals[0].outbound_qty
    ).toBe(200);
    wrapper.unmount();
  });
});
