import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Market from "../index.vue";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

vi.mock("@utils", () => ({ request }));

describe("S&OP market page", () => {
  beforeEach(() => {
    request.mockReset();
  });

  it("shows unconfigured state when API returns 501", async () => {
    request.mockRejectedValue({ response: { status: 501 } });
    const wrapper = mount(Market, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    expect(wrapper.text()).toContain("外部市场数据源尚未接入");
    expect(wrapper.text()).toContain("审计");
    expect(wrapper.text()).toContain("刷新重试");
  });

  it("renders records with source and timestamp when configured", async () => {
    request.mockResolvedValue({
      data: {
        data: [
          {
            title: "AI眼镜行业增长",
            summary: "2026年全球出货量预计突破5000万台",
            source: "IDC",
            observed_at: "2026-09-15T10:00:00Z",
            impact: "high",
          },
        ],
      },
    });
    const wrapper = mount(Market, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    expect(wrapper.text()).toContain("AI眼镜行业增长");
    expect(wrapper.text()).toContain("IDC");
    expect(wrapper.text()).toContain("高");
  });

  it("shows empty state when API returns empty array", async () => {
    request.mockResolvedValue({ data: { data: [] } });
    const wrapper = mount(Market, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    expect(wrapper.text()).toContain("暂无市场热点数据");
  });
});
