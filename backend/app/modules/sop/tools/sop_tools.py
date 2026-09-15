"""Whitelisted Agent tools for first-phase S&OP queries."""

from datetime import date

from langchain_core.tools import tool

from app.modules.sop.database import SessionLocal
from app.modules.sop.domain import SopService


@tool("get_sop_data_status")
def get_sop_data_status() -> str:
    """查询S&OP第一期各数据源的接入、快照和质量状态。不得用本工具查询业务数值。"""
    db = SessionLocal()
    try:
        return SopService(db).get_data_status().model_dump_json()
    finally:
        db.close()


@tool("get_sop_first_phase_report")
def get_sop_first_phase_report(spu_code: str, as_of_date: str = "") -> str:
    """查询单个SPU的第一期固定报表，包含历史出库、激活、预测校验和来源。spu_code必须由用户明确提供。"""
    parsed_date = None
    if as_of_date:
        try:
            parsed_date = date.fromisoformat(as_of_date)
        except ValueError:
            return '{"error":"as_of_date 必须为 YYYY-MM-DD 格式"}'

    db = SessionLocal()
    try:
        report = SopService(db).build_first_phase_report(spu_code, parsed_date)
        if report is None:
            return '{"error":"SPU 不存在或尚未完成标准化入库"}'
        return report.model_dump_json()
    finally:
        db.close()


@tool("query_spu_sales_and_activations")
def query_spu_sales_and_activations(spu_code: str, region: str = "") -> str:
    """查询指定 SPU 的月度出库发货与端侧激活事实数据，支持指定区域筛选。"""
    db = SessionLocal()
    try:
        report = SopService(db).build_first_phase_report(spu_code, region=region)
        if not report or not report.monthly_actuals:
            return f'{{"spu_code":"{spu_code}","data":[],"message":"暂无出库与激活事实"}}'
        data = [m.model_dump() for m in report.monthly_actuals]
        return f'{{"spu_code":"{spu_code}","monthly_actuals":{data}}}'
    finally:
        db.close()


@tool("query_spu_forecast_deviations")
def query_spu_forecast_deviations(spu_code: str) -> str:
    """查询指定 SPU 的月度销售提报预测与统计基线偏差率核验结果，返回风险等级。"""
    db = SessionLocal()
    try:
        report = SopService(db).build_first_phase_report(spu_code)
        if not report or not report.forecast_checks:
            return f'{{"spu_code":"{spu_code}","forecast_checks":[],"message":"暂无预测偏差记录"}}'
        data = [c.model_dump() for c in report.forecast_checks]
        return f'{{"spu_code":"{spu_code}","forecast_checks":{data}}}'
    finally:
        db.close()
