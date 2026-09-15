"""SOP 数据接入与查询（收编自 SopAgent api/routes/sop.py 数据侧接口）"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Security
from sqlalchemy.orm import Session

from app.common.response import JSONResponse, ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute
from app.modules.sop.database import get_db
from app.modules.sop.domain import SopService, WarehouseQueryService
from app.modules.sop.domain.ingestion import SopIngestionService
from app.modules.sop.schemas.sop import (
    SopActivationImportRequest,
    SopDataStatusResponse,
    SopEventImportRequest,
    SopForecastImportRequest,
    SopImportResponse,
    SopSalesImportRequest,
    SopSpuImportRequest,
    SopSpuListResponse,
)

SopDataRouter = APIRouter(route_class=OperationLogRoute, prefix="/data", tags=["SOP 数据接入"])


@SopDataRouter.get("/status", summary="数据源状态", response_model=ResponseSchema[SopDataStatusResponse])
def get_sop_data_status(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:query"]))],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    service = SopService(db)
    response = service.get_data_status()
    service.write_audit(
        username=auth.user.username,
        action="read_data_status",
        resource="sop:data-status",
        result_status="success",
        details={"overall_status": response.overall_status},
    )
    return SuccessResponse(data=response, msg="获取数据源状态成功")


@SopDataRouter.get("/spus", summary="SPU 列表", response_model=ResponseSchema[SopSpuListResponse])
def list_sop_spus(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:query"]))],
    db: Annotated[Session, Depends(get_db)],
    search: Annotated[str, Query(max_length=128)] = "",
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> JSONResponse:
    service = SopService(db)
    response = service.list_spus(search=search, limit=limit)
    service.write_audit(
        username=auth.user.username,
        action="list_spus",
        resource="sop:spus",
        result_status="success",
        details={"search": search, "result_count": response.total},
    )
    return SuccessResponse(data=response, msg="获取 SPU 列表成功")


@SopDataRouter.get("/market/hotspots", summary="市场热点(未接入)")
def get_market_hotspots(
    _: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:query"]))],
) -> None:
    """外部市场数据源尚未接入前保持 501。"""
    raise HTTPException(status_code=501, detail="外部市场数据源尚未接入")


def _audit_import(db: Session, auth: AuthSchema, response: SopImportResponse) -> None:
    SopService(db).write_audit(
        username=auth.user.username,
        action="import_phase_one_data",
        resource=f"sop:import:{response.domain}",
        result_status=response.status,
        details={
            "batch_id": response.batch_id,
            "accepted": response.accepted,
            "rejected": response.rejected,
            "quality_issue_ids": response.quality_issue_ids,
        },
    )


@SopDataRouter.post("/imports/spus", summary="导入 SPU 主数据", response_model=ResponseSchema[SopImportResponse])
def import_spus(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:import"]))],
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[SopSpuImportRequest, Body(...)],
) -> JSONResponse:
    response = SopIngestionService(db).import_spus(payload)
    _audit_import(db, auth, response)
    return SuccessResponse(data=response, msg="SPU 主数据导入完成")


@SopDataRouter.post("/imports/sales", summary="导入销售事实", response_model=ResponseSchema[SopImportResponse])
def import_sales(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:import"]))],
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[SopSalesImportRequest, Body(...)],
) -> JSONResponse:
    response = SopIngestionService(db).import_sales(payload)
    _audit_import(db, auth, response)
    return SuccessResponse(data=response, msg="销售数据导入完成")


@SopDataRouter.post("/imports/activations", summary="导入激活事实", response_model=ResponseSchema[SopImportResponse])
def import_activations(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:import"]))],
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[SopActivationImportRequest, Body(...)],
) -> JSONResponse:
    response = SopIngestionService(db).import_activations(payload)
    _audit_import(db, auth, response)
    return SuccessResponse(data=response, msg="激活数据导入完成")


@SopDataRouter.post("/imports/forecasts", summary="导入预测数据", response_model=ResponseSchema[SopImportResponse])
def import_forecasts(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:import"]))],
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[SopForecastImportRequest, Body(...)],
) -> JSONResponse:
    response = SopIngestionService(db).import_forecasts(payload)
    _audit_import(db, auth, response)
    return SuccessResponse(data=response, msg="预测数据导入完成")


@SopDataRouter.post("/imports/events", summary="导入发生事件", response_model=ResponseSchema[SopImportResponse])
def import_events(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:import"]))],
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[SopEventImportRequest, Body(...)],
) -> JSONResponse:
    response = SopIngestionService(db).import_events(payload)
    _audit_import(db, auth, response)
    return SuccessResponse(data=response, msg="事件数据导入完成")


@SopDataRouter.post("/warehouse/sync", summary="数仓一键同步")
def sync_warehouse(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:data:sync"]))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """从企业只读数仓 (big_data_dw) 同步 SPU、预测与真实已发货订单事实."""
    service = WarehouseQueryService(db)
    result = service.sync_from_warehouse()
    SopService(db).write_audit(
        username=auth.user.username,
        action="warehouse_sync",
        resource="sop:big_data_dw",
        result_status="success",
        details=result,
    )
    return {"message": "数仓数据同步成功", "details": result}
