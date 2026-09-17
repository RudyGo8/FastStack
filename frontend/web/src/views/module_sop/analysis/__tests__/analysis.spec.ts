import ElementPlus from "element-plus";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Analysis from "../index.vue";

describe("S&OP forecast validation page", () => {
  it("clearly identifies the unavailable AI forecast dependency", () => {
    const wrapper = mount(Analysis, { global: { plugins: [ElementPlus] } });

    expect(wrapper.text()).toContain("预测校验功能未接入");
    expect(wrapper.text()).toContain("AI 预测数据将由其他部门统一接入");
    expect(wrapper.text()).toContain("提报预测 vs AI 基线对比矩阵");
  });
});
