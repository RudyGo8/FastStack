from collections.abc import Callable
from dataclasses import dataclass

from app.modules.sop.tools.rag_tools import list_knowledge_documents, search_knowledge_base
from app.modules.sop.tools.sop_tools import (
    get_sop_data_status,
    get_sop_first_phase_report,
    query_spu_forecast_deviations,
    query_spu_sales_and_activations,
)


@dataclass
class ToolSpec:
    name: str
    tool: Callable
    description: str
    tags: list[str]
    source: str | None = None


TOOL_REGISTRY = {
    "get_sop_data_status": ToolSpec(
        name="get_sop_data_status",
        tool=get_sop_data_status,
        description="查询S&OP第一期数据源接入、快照和质量状态",
        tags=["sop", "S&OP", "数据源", "接入状态", "数据质量"],
    ),
    "get_sop_first_phase_report": ToolSpec(
        name="get_sop_first_phase_report",
        tool=get_sop_first_phase_report,
        description="查询指定SPU的历史出库、激活、预测校验和来源追溯固定报表",
        tags=["sop", "S&OP", "SPU", "出库", "激活", "预测", "报表"],
    ),
    "query_spu_sales_and_activations": ToolSpec(
        name="query_spu_sales_and_activations",
        tool=query_spu_sales_and_activations,
        description="查询指定 SPU 的月度出库发货与端侧激活事实数据",
        tags=["sop", "SPU", "出库", "激活", "发货量"],
    ),
    "query_spu_forecast_deviations": ToolSpec(
        name="query_spu_forecast_deviations",
        tool=query_spu_forecast_deviations,
        description="查询指定 SPU 的月度销售提报预测与统计基线偏差率核验结果",
        tags=["sop", "SPU", "预测偏差", "提报", "规则校验", "风险"],
    ),
    "search_knowledge_base": ToolSpec(
        name="search_knowledge_base",
        tool=search_knowledge_base,
        description="查询用户上传文档、知识库、项目资料、内部知识，并返回有依据的检索结果",
        tags=["知识库", "文档", "资料", "上传", "引用", "rag"],
    ),
    "list_knowledge_documents": ToolSpec(
        name="list_knowledge_documents",
        tool=list_knowledge_documents,
        description="列出知识库中已入库的文档清单（文件名、类型、切块数），回答“知识库里有什么文档”类问题",
        tags=["文档列表", "文档清单", "知识库", "文件列表"],
    ),
}
