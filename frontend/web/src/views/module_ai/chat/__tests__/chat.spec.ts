import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Chat from "../components/SopChatPanel.vue";

const { getSessionList, getSessionMessages, deleteSession, streamChatMock } = vi.hoisted(() => ({
  getSessionList: vi.fn(),
  getSessionMessages: vi.fn(),
  deleteSession: vi.fn(),
  streamChatMock: vi.fn(),
}));

vi.mock("@/api/module_ai/sop_chat", () => ({
  SopChatAPI: {
    getSessionList,
    getSessionMessages,
    deleteSession,
  },
  streamChat: streamChatMock,
}));

vi.mock("@/components/display/fa-markdown-renderer/index.vue", () => ({
  default: {
    name: "FaMarkdownRenderer",
    props: ["content"],
    template: '<div class="md">{{ content }}</div>',
  },
}));

describe("S&OP chat page", () => {
  beforeEach(() => {
    getSessionList.mockResolvedValue({
      data: {
        data: {
          sessions: [
            {
              session_id: "s1",
              title: "测试会话",
              updated_at: "2026-09-15T10:00:00Z",
              message_count: 4,
            },
          ],
        },
      },
    });
    getSessionMessages.mockResolvedValue({
      data: {
        data: { messages: [{ type: "human", content: "你好", timestamp: "2026-09-15T10:00:00Z" }] },
      },
    });
    deleteSession.mockResolvedValue({ data: { data: { session_id: "s1", message: "ok" } } });
    streamChatMock.mockResolvedValue(undefined);
  });

  it("renders session list and switches session", async () => {
    const wrapper = mount(Chat, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    expect(getSessionList).toHaveBeenCalled();
    expect(wrapper.text()).toContain("测试会话");
  });

  it("creates a new session and clears messages", async () => {
    const wrapper = mount(Chat, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    await wrapper.find(".session-item").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("你好");

    const newSessionButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("新会话"));
    expect(newSessionButton).toBeDefined();
    await newSessionButton!.trigger("click");
    await flushPromises();

    expect(wrapper.text()).not.toContain("你好");
  });

  it("disables send button while streaming", async () => {
    let resolveStream: () => void;
    streamChatMock.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveStream = resolve;
        })
    );

    const wrapper = mount(Chat, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    const textarea = wrapper.find("textarea");
    await textarea.setValue("测试问题");
    const sendButton = wrapper.findAll("button").find((button) => button.text().includes("发送"));
    expect(sendButton).toBeDefined();
    await sendButton!.trigger("click");

    expect(streamChatMock).toHaveBeenCalled();
    expect(sendButton!.attributes("disabled")).toBeDefined();

    resolveStream!();
    await flushPromises();
  });
});
