"""Authoritative phase-one source catalog derived from docs/sop数据清单.xlsx."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SopSourceDefinition:
    domain: str
    label: str
    source_objects: tuple[str, ...]
    phase_scope: str
    contract_status: str
    note: str = ""


SOURCE_CATALOG: tuple[SopSourceDefinition, ...] = (
    SopSourceDefinition(
        domain="spu_mapping",
        label="SPU 映射与产品谱系",
        source_objects=("import_sales_forecast_spu_model",),
        phase_scope="phase_one_core",
        contract_status="fields_pending",
    ),
    SopSourceDefinition(
        domain="historical_sales",
        label="历史销售与出库",
        source_objects=(
            "dw_a_sal_order_*",
            "dw_a_sal_out*",
            "dw_c_sal_predict_jst_order",
        ),
        phase_scope="phase_one_core",
        contract_status="fields_pending",
        note="订单表：dw_a_sal_order_* / dw_c_sal_predict_jst_order；出库单表：dw_a_sal_out* / dw_c_sal_predict_jst_order。按已发货订单关联产品编码映射，保留真实日粒度出库数量；不补齐无法映射的物料。",
    ),
    SopSourceDefinition(
        domain="forecast",
        label="预测数据",
        source_objects=("dw_sal_predict_accuracy", "import_order_forecast_summary"),
        phase_scope="phase_one_core",
        contract_status="fields_pending",
    ),
    SopSourceDefinition(
        domain="activation",
        label="激活数据",
        source_objects=(
            "big_data_dw.dw_c_base_product_header",
            "big_data_dw.dw_c_base_product_events",
            "big_data_dw.dw_a_device",
        ),
        phase_scope="phase_one_core",
        contract_status="draft_sql_review",
        note="Excel 已提供查询草稿；过滤位置、去重主键和 SPU 编码需确认后固化为只读视图。",
    ),
    SopSourceDefinition(
        domain="inventory",
        label="库存与在途",
        source_objects=("dws_spu_material_stock_detail_semi",),
        phase_scope="phase_one_extension",
        contract_status="fields_pending",
    ),
    SopSourceDefinition(
        domain="lifecycle",
        label="生命周期及迭代关系",
        source_objects=("BI 报表", "PPMO 在线文档", "中长期产品规划布阵 3.0"),
        phase_scope="phase_one_extension",
        contract_status="source_pending",
        note="来源完整性与更新及时性待业务 Owner 确认。",
    ),
    SopSourceDefinition(
        domain="sales_window",
        label="开始售卖与停止售卖时间",
        source_objects=(),
        phase_scope="phase_one_extension",
        contract_status="source_pending",
    ),
    SopSourceDefinition(
        domain="competitor",
        label="竞品数据",
        source_objects=("dw_bd_competitor_pool", "dw_bd_competitor_dealer_price"),
        phase_scope="phase_one_extension",
        contract_status="fields_pending",
        note="来源包含系统数据和人工填报。",
    ),
    SopSourceDefinition(
        domain="capacity",
        label="产能约束",
        source_objects=("import_prod_line_capacity",),
        phase_scope="connection_only",
        contract_status="fields_pending",
        note="第一期仅预留接入，供需缺口和情景分析进入 V2。",
    ),
)

CORE_DOMAINS = frozenset(source.domain for source in SOURCE_CATALOG if source.phase_scope == "phase_one_core")
