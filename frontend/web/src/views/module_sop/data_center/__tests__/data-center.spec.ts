import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import DataCenter from "../index.vue";

const { getDataStatus, getSpuList, getSnapshotList } = vi.hoisted(() => ({
  getDataStatus: vi.fn(),
  getSpuList: vi.fn(),
  getSnapshotList: vi.fn(),
}));
vi.mock("@/api/module_sop/data", () => ({
  SopDataAPI: {
    getDataStatus,
    getSpuList,
    importSpus: vi.fn(),
    importSales: vi.fn(),
    importActivations: vi.fn(),
    importForecasts: vi.fn(),
    syncWarehouse: vi.fn(),
  },
}));
vi.mock("@/api/module_sop/report", () => ({
  SopReportAPI: { getSnapshotList, generateSnapshots: vi.fn() },
}));

describe("S&OP data center", () => {
  it("provides source, import, SPU, rule, and snapshot workflows", async () => {
    getDataStatus.mockResolvedValue({
      data: {
        data: {
          overall_status: "partial",
          source_connection_configured: true,
          open_quality_issues: 0,
          sources: [
            {
              domain: "forecast",
              label: "预测数据",
              source_objects: ["real_forecast_view"],
              phase_scope: "phase_one_core",
              contract_status: "fields_pending",
              ingestion_status: "completed",
              latest_snapshot_at: "2026-09-15 11:34:02",
              max_business_date: "2027-08-01",
              record_count: 1113,
              note: "",
            },
            {
              domain: "inventory",
              label: "库存与在途",
              source_objects: ["real_inventory_view"],
              phase_scope: "phase_one_extension",
              contract_status: "fields_pending",
              ingestion_status: "not_started",
              latest_snapshot_at: null,
              max_business_date: null,
              record_count: 0,
              note: "字段映射待确认",
            },
          ],
        },
      },
    });
    getSpuList.mockResolvedValue({ data: { data: { items: [], total: 0 } } });
    getSnapshotList.mockResolvedValue({ data: { data: [] } });
    const wrapper = mount(DataCenter, { global: { plugins: [ElementPlus] } });
    await flushPromises();
    const text = wrapper.text();
    expect(text).toContain("企业数仓连接正常");
    expect(text).toContain("一期核心：1/1 已同步");
    expect(text).toContain("扩展域待接入");
    for (const label of ["数据源同步", "数据导入", "SPU 主数据", "校验规则", "会前数据快照"])
      expect(text).toContain(label);
    await wrapper
      .findAll(".el-tabs__item")
      .find((item) => item.text().includes("SPU 主数据"))
      ?.trigger("click");
    expect(wrapper.text()).toContain("SPU 品类主数据字典");
    await wrapper
      .findAll(".el-tabs__item")
      .find((item) => item.text().includes("校验规则"))
      ?.trigger("click");
    expect(wrapper.text()).toContain("预测校验默认口径");
    await wrapper
      .findAll(".el-tabs__item")
      .find((item) => item.text().includes("会前数据快照"))
      ?.trigger("click");
    expect(wrapper.text()).toContain("T-1 业务基线");
    expect(wrapper.text()).toContain("不可变快照历史记录");
  });
});
