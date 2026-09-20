import ElementPlus, { ElMessageBox } from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Memory from "../index.vue";

vi.hoisted(() => {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn(() => ({
      addEventListener: vi.fn(),
      matches: false,
      removeEventListener: vi.fn(),
    })),
  });
});

const { deleteSession, getSessionList, getSessionMessages, legacyGetSessionList } = vi.hoisted(() => ({
  deleteSession: vi.fn(),
  getSessionList: vi.fn(),
  getSessionMessages: vi.fn(),
  legacyGetSessionList: vi.fn(),
}));

vi.mock("@/api/module_ai/sop_chat", () => ({
  SopChatAPI: { deleteSession, getSessionList, getSessionMessages },
}));
vi.mock("@/api/module_ai/chat", () => ({
  default: {
    getSessionList: legacyGetSessionList,
    getSessionDetail: vi.fn(),
    deleteSession: vi.fn(),
    createSession: vi.fn(),
    updateSession: vi.fn(),
  },
}));

const sessions = [
  {
    session_id: "s_inventory",
    title: "库存风险复盘",
    updated_at: "2026-09-15T10:30:00Z",
    message_count: 2,
  },
];

describe("AI session history", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSessionList.mockResolvedValue({ data: { data: { sessions } } });
    getSessionMessages.mockResolvedValue({
      data: {
        data: {
          messages: [
            { type: "human", content: "库存有什么风险？", timestamp: "2026-09-15T10:29:00Z" },
            { type: "ai", content: "当前需关注积压库存。", timestamp: "2026-09-15T10:30:00Z" },
          ],
        },
      },
    });
    deleteSession.mockResolvedValue({ data: { data: { session_id: "s_inventory" } } });
    legacyGetSessionList.mockResolvedValue({ data: { data: { list: [], total: 0 } } });
  });

  it("lists sessions from the SOP chat store", async () => {
    const wrapper = mount(Memory, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    expect(wrapper.text()).toContain("库存风险复盘");
    expect(wrapper.text()).toContain("2 条");
    expect(getSessionList).toHaveBeenCalledOnce();
    expect(legacyGetSessionList).not.toHaveBeenCalled();
  });

  it("loads the selected SOP session messages", async () => {
    const wrapper = mount(Memory, {
      attachTo: document.body,
      global: { plugins: [ElementPlus] },
    });
    await flushPromises();

    const detailButton = wrapper.findAll("button").find((button) => button.text().includes("详情"));
    await detailButton!.trigger("click");
    await flushPromises();

    expect(getSessionMessages).toHaveBeenCalledWith("s_inventory");
    expect(document.body.textContent).toContain("库存有什么风险？");
    expect(document.body.textContent).toContain("当前需关注积压库存。");
    wrapper.unmount();
  });

  it("deletes one SOP session by session id", async () => {
    vi.spyOn(ElMessageBox, "confirm").mockResolvedValue("confirm" as never);
    const wrapper = mount(Memory, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    const deleteButton = wrapper.findAll("button").find((button) => button.text().includes("删除"));
    await deleteButton!.trigger("click");
    await flushPromises();

    expect(deleteSession).toHaveBeenCalledWith("s_inventory");
    expect(getSessionList).toHaveBeenCalledTimes(2);
  });
});
