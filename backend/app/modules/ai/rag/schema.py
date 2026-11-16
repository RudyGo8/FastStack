"""RAG 接口的请求/响应模型。"""

from pydantic import BaseModel, Field


class RagIngestIn(BaseModel):
    """文本入库（来自上传解析或直接提交）。"""

    filename: str = Field(min_length=1, max_length=255, description="来源文件名")
    content: str = Field(min_length=1, description="文档正文")
    file_type: str = Field(default="", max_length=50, description="来源文件类型")
    tenant_id: str = Field(default="", max_length=64, description="租户/项目标识，留空用默认值")


class RagIngestOut(BaseModel):
    filename: str
    chunks: int = Field(description="写入的叶子分块数")
    parents: int = Field(description="写入的父分块数")


class RagDocumentOut(BaseModel):
    filename: str
    file_type: str = ""
    chunks: int = 0


class RagDocumentListOut(BaseModel):
    documents: list[RagDocumentOut] = Field(default_factory=list)


class RagSearchIn(BaseModel):
    query: str = Field(min_length=1, description="检索问题")
    top_k: int = Field(default=0, ge=0, le=50, description="召回条数，0 表示用默认配置")
    tenant_id: str = Field(default="", max_length=64, description="租户/项目标识")


class RagHitOut(BaseModel):
    chunk_id: str
    text: str = Field(description="命中叶子块正文")
    score: float
    filename: str
    file_type: str = ""
    page_number: int = 0
    parent_text: str = Field(default="", description="回溯到的父块正文，供引用时补全上下文")


class RagSearchOut(BaseModel):
    hits: list[RagHitOut] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="本次结果涉及的来源文件")
