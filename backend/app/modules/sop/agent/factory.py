from app.modules.sop.config import (
    AGENT_RECURSION_LIMIT,
    ARK_API_KEY,
    BASE_URL,
    FALLBACK_MODEL,
    MAIN_MODEL_THINKING,
    MODEL,
)
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

SOP_SYSTEM_PROMPT = """你是由rudy开发的智能助手。

你的职责是帮助业务人员查询单 SPU 的历史出库、激活、预测校验、数据质量和来源，并基于已经计算完成的事实生成清晰中文解释。你也可以通过知识库回答制度、口径、会议纪要和历史决策问题。

【事实与工具边界】
1. 用户询问 SPU、出库、激活、销售预测、数据接入或第一期报表时，必须调用对应的 S&OP 白名单工具。
2. 用户询问制度、口径、文档、方案、会议纪要或历史决策时，必须调用 search_knowledge_base。
3. 不得自行编造 SPU、销量、激活量、预测、库存、日期、来源或得分。
4. 不得自行计算或修改工具返回的业务数值；SQL 与确定性规则的结果是唯一数值依据。
5. 工具返回 missing_domains、not_ready、not_evaluable 或数据未就绪时，必须如实说明，不能用估计值补齐。
6. 回答数值结论时说明来源表和快照时间；没有来源及时点，不输出数值结论。
7. 明确区分“事实数据”“规则校验”和“AI 辅助解释”。

【业务红线】
1. AI 不输出自创预测，不替代现有预测模型和销售提报责任。
2. AI 不直接下达采购、备货、库存处置或产品上下市指令。
3. 第一期聚焦历史出库发货、端侧激活、预测校验和数据血缘追溯；超出范围的数据与指标必须如实告知数据未接入。
4. 默认规则版本带 draft 表示尚待业务 Owner 会签，不得表述为正式业务口径。
5. 必须是真实数据，没有数据就说数据不够，不要编造数据或预测。

【回答结构】
优先按“结论—事实依据—异常与规则—缺失项—建议业务确认事项”的顺序回答。建议只能作为供人审核的辅助意见。

对于寒暄、通用常识、普通编程问题，可以直接简洁回答。
"""


def _build_model(model_name: str):
    return init_chat_model(
        model=model_name,
        model_provider="openai",
        api_key=ARK_API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
        extra_body={"enable_thinking": MAIN_MODEL_THINKING},
    )


_model = None


def _get_model():
    # 惰性构建：模块导入不依赖 API Key，首次对话时才实例化模型
    global _model
    if _model is None:
        _model = _build_model(MODEL)
        if FALLBACK_MODEL:
            _model = _model.with_fallbacks([_build_model(FALLBACK_MODEL)])
    return _model


def create_agent_instance(tools: list | None = None):
    if not tools:
        raise ValueError("必须传入非空 tools 列表")

    model = _get_model()
    agent = create_agent(model=model, tools=tools, system_prompt=SOP_SYSTEM_PROMPT)
    return agent, model


def get_model():
    return _get_model()


def get_recursion_limit() -> int:
    return AGENT_RECURSION_LIMIT
