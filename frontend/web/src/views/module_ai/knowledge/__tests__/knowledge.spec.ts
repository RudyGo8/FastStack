import ElementPlus from "element-plus";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Knowledge from "../index.vue";

const { listDocuments, batchUpload, getChunks, deleteDocument } = vi.hoisted(() => ({
  listDocuments: vi.fn(),
  batchUpload: vi.fn(),
  getChunks: vi.fn(),
  deleteDocument: vi.fn(),
}));

vi.mock("@/api/module_ai/document", () => ({
  SopDocumentAPI: {
    list: listDocuments,
    batchUpload,
    getChunks,
    delete: deleteDocument,
  },
}));

describe("S&OP knowledge page", () => {
  beforeEach(() => {
    listDocuments.mockResolvedValue({
      data: {
        data: {
          documents: [
            { filename: "policy.pdf", file_type: "pdf", chunk_count: 4 },
            { filename: "forecast.xlsx", file_type: "xlsx", chunk_count: 12 },
          ],
        },
      },
    });
    getChunks.mockResolvedValue({
      data: {
        data: {
          filename: "policy.pdf",
          chunks: [
            {
              chunk_id: "c1",
              chunk_idx: 0,
              text_preview: "Preview text",
              file_type: "pdf",
              page_number: 1,
              chunk_level: 0,
            },
          ],
        },
      },
    });
    batchUpload.mockResolvedValue({
      data: { data: { total: 1, succeeded: 1, failed: 0, results: [], message: "ok" } },
    });
    deleteDocument.mockResolvedValue({
      data: { data: { filename: "policy.pdf", chunks_deleted: 4, message: "ok" } },
    });
  });

  it("renders metrics, file type badges, batch upload, and refresh", async () => {
    const wrapper = mount(Knowledge, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    expect(wrapper.text()).toContain("文档数量");
    expect(wrapper.text()).toContain("切片总数");
    expect(wrapper.text()).toContain("索引状态");
    expect(wrapper.text()).toContain("批量上传");
    expect(wrapper.text()).toContain("刷新");
    expect(wrapper.text()).toContain("policy.pdf");
    expect(wrapper.text()).toContain("forecast.xlsx");
    expect(wrapper.text()).toContain("PDF");
    expect(wrapper.text()).toContain("XLSX");
  });

  it("opens chunk drawer and shows chunk previews", async () => {
    const wrapper = mount(Knowledge, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    const previewButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("查看分块"));
    expect(previewButton).toBeDefined();
    await previewButton!.trigger("click");
    await flushPromises();

    expect(getChunks).toHaveBeenCalledWith("policy.pdf");
    expect(wrapper.text()).toContain("Preview text");
  });

  it("shows backend error text when document list fails", async () => {
    listDocuments.mockRejectedValueOnce({ response: { data: { detail: "向量库连接失败" } } });
    const wrapper = mount(Knowledge, { global: { plugins: [ElementPlus] } });
    await flushPromises();

    expect(wrapper.text()).toContain("向量库连接失败");
  });
});
