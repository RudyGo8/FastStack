import ElementPlus, { ElMessage } from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SopChatPanel from "../components/SopChatPanel.vue";

const { deleteSession, getSessionList, getSessionMessages, streamChat } = vi.hoisted(() => ({
  deleteSession: vi.fn(),
  getSessionList: vi.fn(),
  getSessionMessages: vi.fn(),
  streamChat: vi.fn(),
}));

vi.mock("@/api/module_ai/sop_chat", () => ({
  SopChatAPI: { deleteSession, getSessionList, getSessionMessages },
  streamChat,
}));

const global = {
  plugins: [ElementPlus],
  stubs: { FaMarkdownRenderer: { template: '<div class="markdown-stub">{{ content }}</div>', props: ["content"] } },
  config: { errorHandler: vi.fn() },
};

describe("SOP AI chat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSessionList.mockResolvedValue({ data: { data: { sessions: [] } } });
    getSessionMessages.mockResolvedValue({ data: { data: { messages: [] } } });
    deleteSession.mockResolvedValue({ data: { data: {} } });
  });

  it("restores the composer and reports an error when the stream request rejects", async () => {
    streamChat.mockRejectedValueOnce(new Error("network down"));
    const errorMessage = vi.spyOn(ElMessage, "error").mockImplementation(() => undefined as never);
    const wrapper = mount(SopChatPanel, { global });
    await flushPromises();

    const textarea = wrapper.get("textarea");
    await textarea.setValue("检查库存风险");
    await wrapper.get(".send-btn").trigger("click");
    await flushPromises();

    expect(wrapper.get("textarea").attributes("disabled")).toBeUndefined();
    expect(wrapper.get(".composer-box").classes()).not.toContain("disabled");
    await wrapper.get("textarea").setValue("重新提问");
    expect(wrapper.get(".send-btn").attributes("disabled")).toBeUndefined();
    expect(errorMessage).toHaveBeenCalledWith("network down");
  });
});
