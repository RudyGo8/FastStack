import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import BusinessData from "../business_data/index.vue";

const { getDataStatus, getSpuList } = vi.hoisted(() => ({
  getDataStatus: vi.fn(),
  getSpuList: vi.fn(),
}));
vi.mock("@/api/module_sop/data", () => ({
  SopDataAPI: { getDataStatus, getSpuList },
}));

describe("S&OP business data", () => {
  it("provides ordinary users a read-only SPU and source overview", async () => {
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
    getSpuList.mockResolvedValue({
      data: {
        data: {
          items: [
            {
              spu_code: "C706",
              spu_name: "AI眼镜",
              product_line: "AR",
              brand: "Test",
              category: "消费",
              lifecycle_stage: "growth",
            },
          ],
          total: 1,
        },
      },
    });
    const wrapper = mount(BusinessData, { global: { plugins: [ElementPlus] } });
    await flushPromises();
    const text = wrapper.text();
    expect(text).toContain("业务数据（只读）");
    expect(text).toContain("数据导入与配置请联系管理员");
    expect(text).toContain("C706");
    expect(text).toContain("AI眼镜");
    await wrapper
      .findAll(".el-tabs__item")
      .find((item) => item.text().includes("数据源状态"))
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("预测数据");
    expect(wrapper.text()).toContain("同步完成");
  });
});
