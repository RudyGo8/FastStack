"""SOP 报告：一期会议报告、快照固化与 docx 导出（收编自 SopAgent api/routes/sop.py 报告侧接口）"""

import calendar
import urllib.parse
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Security
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.response import JSONResponse, ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute
from app.modules.sop.database import get_db
from app.modules.sop.domain import SopService, SopSnapshotService
from app.modules.sop.domain.docx_exporter import build_sop_report_docx
from app.modules.sop.domain.warehouse_sync import WarehouseQueryService, WarehouseSyncInProgress
from app.modules.sop.schemas.sop import (
    SopDimensionOptionsResponse,
    SopFirstPhaseReportResponse,
    SopReportSnapshotDetail,
    SopReportSnapshotSummary,
    SopSnapshotGenerateRequest,
    SopSnapshotGenerateResponse,
)

SopReportRouter = APIRouter(route_class=OperationLogRoute, prefix="/report", tags=["SOP 报告快照"])


MONTH_PATTERN = r"^[1-9][0-9]{3}-(0[1-9]|1[0-2])$"


def _period_dates(start_month: str | None, end_month: str | None) -> tuple[date | None, date | None]:
    if start_month and end_month and start_month > end_month:
        raise HTTPException(status_code=422, detail="开始月份不能晚于结束月份")
    start_date = date.fromisoformat(f"{start_month}-01") if start_month else None
    end_date = None
    if end_month:
        first = date.fromisoformat(f"{end_month}-01")
        end_date = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    return start_date, end_date


@SopReportRouter.post("/refresh", summary="刷新真实报告数据", response_model=ResponseSchema[dict])
def refresh_report_data(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:query"]))],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """刷新固定配置的只读数仓报告缓存，不接受导入记录、SQL 或来源配置。"""
    try:
        result = WarehouseQueryService(db).sync_from_warehouse()
    except WarehouseSyncInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    SopService(db).write_audit(
        username=auth.user.username,
        action="refresh_report_data",
        resource="sop:report-cache",
        result_status="success",
        details=result,
    )
    return SuccessResponse(data=result, msg="真实报告数据刷新成功")


@SopReportRouter.get("/spus/{spu_code}/dimensions", summary="SPU 维度选项", response_model=ResponseSchema[SopDimensionOptionsResponse])
def get_sop_dimension_options(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:query"]))],
    db: Annotated[Session, Depends(get_db)],
    spu_code: str,
) -> JSONResponse:
    service = SopService(db)
    response = service.list_dimension_options(spu_code)
    if response is None:
        raise HTTPException(status_code=404, detail="SPU 不存在或尚未完成标准化入库")
    service.write_audit(
        username=auth.user.username,
        action="read_dimension_options",
        resource=f"sop:spu:{spu_code}:dimensions",
        result_status="success",
        details={"regions": len(response.regions), "channels": len(response.channels)},
    )
    return SuccessResponse(data=response, msg="获取维度选项成功")


@SopReportRouter.get("/spus/{spu_code}/first-phase", summary="一期会议报告", response_model=ResponseSchema[SopFirstPhaseReportResponse])
def get_first_phase_report(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:query"]))],
    db: Annotated[Session, Depends(get_db)],
    spu_code: str,
    as_of_date: Annotated[date | None, Query()] = None,
    region: Annotated[str, Query(max_length=128)] = "",
    channel: Annotated[str, Query(max_length=128)] = "",
    start_month: Annotated[str | None, Query(pattern=MONTH_PATTERN)] = None,
    end_month: Annotated[str | None, Query(pattern=MONTH_PATTERN)] = None,
) -> JSONResponse:
    # 工作台与会议报告始终使用同一份已同步事实；固化快照通过快照接口单独读取。
    start_date, end_date = _period_dates(start_month, end_month)
    service = SopService(db)
    response = service.build_first_phase_report(
        spu_code=spu_code,
        as_of_date=as_of_date,
        region=region,
        channel=channel,
        start_date=start_date,
        end_date=end_date,
    )
    source_type = "source"

    if response is None:
        service = SopService(db)
        service.write_audit(
            username=auth.user.username,
            action="read_first_phase_report",
            resource=f"sop:spu:{spu_code}",
            result_status="not_found",
        )
        raise HTTPException(status_code=404, detail="SPU 不存在或尚未完成标准化入库")

    service = SopService(db)
    service.write_audit(
        username=auth.user.username,
        action="read_first_phase_report",
        resource=f"sop:spu:{spu_code}",
        result_status=response.completeness_status,
        details={
            "as_of_date": response.as_of_date.isoformat(),
            "missing_domains": response.missing_domains,
            "report_version": response.report_version,
            "region": region,
            "channel": channel,
            "source": source_type,
            "start_month": start_month,
            "end_month": end_month,
        },
    )
    return SuccessResponse(data=response, msg="获取报告成功")


@SopReportRouter.get("/spus/{spu_code}/export-docx", summary="导出 Word 报告")
def export_first_phase_report_docx(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:export"]))],
    db: Annotated[Session, Depends(get_db)],
    spu_code: str,
    as_of_date: Annotated[date | None, Query()] = None,
    region: Annotated[str, Query(max_length=128)] = "",
    channel: Annotated[str, Query(max_length=128)] = "",
    start_month: Annotated[str | None, Query(pattern=MONTH_PATTERN)] = None,
    end_month: Annotated[str | None, Query(pattern=MONTH_PATTERN)] = None,
) -> StreamingResponse:
    """导出排版规整的飞书/Word (.docx) 格式会议报告."""
    start_date, end_date = _period_dates(start_month, end_month)
    service = SopService(db)
    response = service.build_first_phase_report(
        spu_code=spu_code,
        as_of_date=as_of_date,
        region=region,
        channel=channel,
        start_date=start_date,
        end_date=end_date,
    )
    if response is None:
        raise HTTPException(status_code=404, detail="SPU 不存在或尚未完成标准化入库")

    report_dict = response.model_dump()
    docx_stream = build_sop_report_docx(report_dict)

    filename = f"SOP_会议报告_{spu_code}_{response.as_of_date}.docx"
    encoded_filename = urllib.parse.quote(filename)

    service.write_audit(
        username=auth.user.username,
        action="export_docx_report",
        resource=f"sop:spu:{spu_code}:docx",
        result_status="success",
        details={"spu_code": spu_code, "filename": filename},
    )

    return StreamingResponse(
        docx_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@SopReportRouter.post("/snapshots/generate", summary="生成快照", response_model=ResponseSchema[SopSnapshotGenerateResponse])
def generate_sop_snapshots(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:generate"]))],
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[SopSnapshotGenerateRequest | None, Body()] = None,
) -> JSONResponse:
    """手动或定时触发会前数据快照生成（默认提前一天晚上 T-1 数据截止）."""
    payload = payload or SopSnapshotGenerateRequest()
    service = SopSnapshotService(db)
    response = service.generate_nightly_snapshots(
        spu_code=payload.spu_code,
        as_of_date=payload.as_of_date,
        report_version=payload.report_version,
    )
    SopService(db).write_audit(
        username=auth.user.username,
        action="generate_snapshots",
        resource="sop:snapshots:generate",
        result_status="success",
        details={
            "as_of_date": str(response.as_of_date),
            "report_version": response.report_version,
            "generated_count": response.generated_count,
        },
    )
    return SuccessResponse(data=response, msg="快照生成完成")


@SopReportRouter.get("/snapshots", summary="快照列表", response_model=ResponseSchema[list[SopReportSnapshotSummary]])
def list_sop_snapshots(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:query"]))],
    db: Annotated[Session, Depends(get_db)],
    spu_code: Annotated[str | None, Query()] = None,
    as_of_date: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> JSONResponse:
    """查询不可变数据快照列表."""
    service = SopSnapshotService(db)
    results = service.list_snapshots(spu_code=spu_code, as_of_date=as_of_date, limit=limit)
    return SuccessResponse(data=results, msg="获取快照列表成功")


@SopReportRouter.get("/snapshots/{snapshot_id}", summary="快照详情", response_model=ResponseSchema[SopReportSnapshotDetail])
def get_sop_snapshot_detail(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:query"]))],
    db: Annotated[Session, Depends(get_db)],
    snapshot_id: int,
) -> JSONResponse:
    """获取指定快照的完整内容."""
    service = SopSnapshotService(db)
    snapshot = service.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="指定快照不存在")
    return SuccessResponse(data=snapshot, msg="获取快照详情成功")


@SopReportRouter.get("/spus/{spu_code}/latest-snapshot", summary="SPU 最新快照", response_model=ResponseSchema[SopReportSnapshotDetail])
def get_spu_latest_snapshot(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:report:query"]))],
    db: Annotated[Session, Depends(get_db)],
    spu_code: str,
    as_of_date: Annotated[date | None, Query()] = None,
) -> JSONResponse:
    """获取指定 SPU 最新的会前固化快照."""
    service = SopSnapshotService(db)
    snapshot = service.get_latest_snapshot(spu_code, as_of_date=as_of_date)
    if not snapshot:
        raise HTTPException(status_code=404, detail="该 SPU 暂无可用的固化快照")
    return SuccessResponse(data=snapshot, msg="获取最新快照成功")
