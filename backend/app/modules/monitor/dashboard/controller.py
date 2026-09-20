from typing import Annotated

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import LoginStatisticsSchema, LoginTrendSchema, OperationStatisticsSchema, StatisticsSchema
from .service import DashboardService

DashboardRouter = APIRouter(route_class=OperationLogRoute, prefix="/dashboard", tags=["工作台"])


@DashboardRouter.get("/statistics", summary="获取工作台统计卡片数据", response_model=ResponseSchema[StatisticsSchema])
async def get_dashboard_statistics_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_monitor:dashboard:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result_dict: StatisticsSchema = await DashboardService.get_statistics(db=db, auth=auth)
    return SuccessResponse(data=result_dict, msg="获取工作台统计卡片数据成功")


@DashboardRouter.get("/login/statistics", summary="获取登录统计数据", response_model=ResponseSchema[LoginStatisticsSchema])
async def get_login_statistics_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_monitor:dashboard:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result_dict: LoginStatisticsSchema = await DashboardService.get_login_statistics(db=db, auth=auth)
    return SuccessResponse(data=result_dict, msg="获取登录统计数据成功")


@DashboardRouter.get("/login/trend", summary="获取登录趋势数据", response_model=ResponseSchema[LoginTrendSchema])
async def get_login_trend_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_monitor:dashboard:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result_dict: LoginTrendSchema = await DashboardService.get_login_trend(db=db, auth=auth)
    return SuccessResponse(data=result_dict, msg="获取登录趋势数据成功")


@DashboardRouter.get(
    "/operation/statistics", summary="获取操作统计数据", response_model=ResponseSchema[OperationStatisticsSchema]
)
async def get_operation_statistics_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_monitor:dashboard:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result_dict: OperationStatisticsSchema = await DashboardService.get_operation_statistics(db=db, auth=auth)
    return SuccessResponse(data=result_dict, msg="获取操作统计数据成功")
