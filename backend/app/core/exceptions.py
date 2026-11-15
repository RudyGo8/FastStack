from functools import wraps
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import DisconnectionError, IntegrityError, InterfaceError, SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.common.enums import RET, EnvironmentEnum
from app.common.response import ErrorResponse
from app.config.setting import settings
from app.core.logger import logger


def require_superadmin(func):
    """装饰器：仅超级管理员可调用 Service 方法。

    自动校验 ``self.auth.user.is_superuser`` 属性，非超管直接抛出 403。
    适用于实例方法（``Service(auth).xxx(...)``），由 ``self.auth`` 取认证上下文。

    用法:
        class XxxService:
            def __init__(self, auth: AuthSchema) -> None:
                self.auth = auth

            @require_superadmin
            async def create(self, data: ...) -> ...:
                ...
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self.auth.user or not self.auth.user.is_superuser:
            raise CustomException(msg="仅平台管理员可操作")
        return await func(self, *args, **kwargs)

    return wrapper


# starlette 新版本把 HTTP_422_UNPROCESSABLE_ENTITY 标为弃用，这里取新常量并兼容旧版本，
# 避免模块导入期就打 DeprecationWarning
_HTTP_422: int = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

# 业务错误码 → HTTP 状态码：**HTTP 语义的唯一事实来源**。
# 约定（t16）：
# - 业务代码只传 code（`raise CustomException(msg=..., code=...)`），构造器不接受 status_code；
# - 本表未命中的 code 才会落到 _DEFAULT_BUSINESS_STATUS（仅为「新增 code 忘了登记」的安全网，
#   不应作为正常路径依赖）；
# - 历史上 status_code 默认 500 让「验证码过期」「参数校验失败」也返回 500，客户端无法区分
#   「我错了」与「服务器坏了」，监控/告警同样被污染，故收敛到本表。
_CODE_TO_HTTP_STATUS: dict[int, int] = {
    # ① 默认业务异常码：客户端可修正 → 400
    RET.EXCEPTION.code: status.HTTP_400_BAD_REQUEST,
    # ② 数值本身就是 HTTP 状态码的 RET 成员：显式登记（不再依赖安全网兜底）
    RET.BAD_REQUEST.code: status.HTTP_400_BAD_REQUEST,
    RET.UNAUTHORIZED.code: status.HTTP_401_UNAUTHORIZED,
    RET.FORBIDDEN.code: status.HTTP_403_FORBIDDEN,
    RET.NOT_FOUND.code: status.HTTP_404_NOT_FOUND,
    RET.BAD_METHOD.code: status.HTTP_405_METHOD_NOT_ALLOWED,
    RET.NOT_ACCEPTABLE.code: status.HTTP_406_NOT_ACCEPTABLE,
    RET.CONFLICT.code: status.HTTP_409_CONFLICT,
    RET.GONE.code: status.HTTP_410_GONE,
    RET.PRECONDITION_FAILED.code: status.HTTP_412_PRECONDITION_FAILED,
    RET.UNSUPPORTED_MEDIA_TYPE.code: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    RET.UNPROCESSABLE_ENTITY.code: _HTTP_422,
    RET.TOO_MANY_REQUESTS.code: status.HTTP_429_TOO_MANY_REQUESTS,
    RET.INTERNAL_SERVER_ERROR.code: status.HTTP_500_INTERNAL_SERVER_ERROR,
    RET.NOT_IMPLEMENTED.code: status.HTTP_501_NOT_IMPLEMENTED,
    RET.BAD_GATEWAY.code: status.HTTP_502_BAD_GATEWAY,
    RET.SERVICE_UNAVAILABLE.code: status.HTTP_503_SERVICE_UNAVAILABLE,
    RET.GATEWAY_TIMEOUT.code: status.HTTP_504_GATEWAY_TIMEOUT,
    RET.HTTP_VERSION_NOT_SUPPORTED.code: status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED,
    # ③ 自定义业务码
    RET.DATAEXIST.code: status.HTTP_409_CONFLICT,
    RET.PARAMERR.code: status.HTTP_400_BAD_REQUEST,
    RET.TIMEOUT.code: status.HTTP_504_GATEWAY_TIMEOUT,
    RET.RATE_LIMIT_EXCEEDED.code: status.HTTP_429_TOO_MANY_REQUESTS,
    # ④ 认证类业务码（对应前端 ResultEnum）
    RET.INVALID_TOKEN.code: status.HTTP_401_UNAUTHORIZED,
    RET.EXPIRED_TOKEN.code: status.HTTP_401_UNAUTHORIZED,
    RET.INVALID_CREDENTIALS.code: status.HTTP_401_UNAUTHORIZED,
    RET.TOKEN_EXPIRED.code: status.HTTP_401_UNAUTHORIZED,
    RET.NO_PERMISSION.code: status.HTTP_403_FORBIDDEN,
    # ⑤ 显式声明为服务端故障的业务码（供极少数已确认属服务端故障的业务场景使用）
    RET.SERVERERR.code: status.HTTP_500_INTERNAL_SERVER_ERROR,
}

# 未登记业务码的安全网：按「客户端请求错误」处理（正常路径应命中上面的表；新增 RET 码请同步登记）
_DEFAULT_BUSINESS_STATUS: int = status.HTTP_400_BAD_REQUEST


def resolve_http_status(code: int | None) -> int:
    """把业务错误码解析为 HTTP 状态码。

    参数:
    - code (int | None): 业务错误码。

    返回:
    - int: 对应的 HTTP 状态码；未映射的码返回 _DEFAULT_BUSINESS_STATUS。
    """
    if code is None:
        return _DEFAULT_BUSINESS_STATUS
    return _CODE_TO_HTTP_STATUS.get(int(code), _DEFAULT_BUSINESS_STATUS)


class CustomException(Exception):
    """业务异常：系统内**唯一**的业务错误写法是 ``raise CustomException(msg=..., code=...)``。

    约定（t19）：
    - 构造器不接受 ``status_code``：HTTP 状态由 ``code`` 经 :func:`resolve_http_status` 推导
      （``status_code`` 只作只读派生属性），从结构上杜绝「业务码 + 显式状态码」两个事实来源；
    - **意外异常不要在这里包装**：让原始异常冒泡，由全局 ``Exception`` / ``SQLAlchemyError``
      处理器统一映射为 5xx + 通用文案 + 日志；需要运维上下文时在抛出处
      ``logger.exception("<业务动作>失败")`` 后再 ``raise``（保留原始异常类型）；
    - 宽泛 ``except`` 若确实要把异常转换成业务错误，必须先 ``except CustomException: raise``。
    """

    def __init__(
        self,
        msg: str = RET.EXCEPTION.msg,
        code: int = RET.EXCEPTION.code,
        data: Any | None = None,
        success: bool = False,
    ) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg
        self.data = data
        self.success = success
        # 只读派生属性：HTTP 状态一律由 code 经映射表推导（构造器不再接受 status_code）
        self.status_code = resolve_http_status(code)

    def __str__(self) -> str:
        return self.msg


# 连接类故障的文案特征（DBAPI 驱动差异大，异常类型优先、文案兜底）
_CONNECTION_HINTS: tuple[str, ...] = (
    "connect",
    "connection",
    "server has gone away",
    "lost connection",
    "connection refused",
    "connection reset",
    "pool",
    "timed out",
)


def _is_connection_detail(detail: str | None) -> bool:
    """判断异常细节是否属于「连接类」故障（→ 503 而不是 500）。

    参数:
    - detail (str | None): 驱动返回的原始错误文本。

    返回:
    - bool: 是否连接类。
    """
    text = (detail or "").lower()
    return any(hint in text for hint in _CONNECTION_HINTS)


def handle_exception(app: FastAPI) -> None:
    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException) -> JSONResponse:
        # 4xx 是「客户端可修正」的业务结果，5xx 才是服务端故障：分级记录，
        # 避免每个校验失败都打 ERROR 把真正的故障信号淹没。
        log = logger.error if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR else logger.warning
        log(
            "[自定义异常] {} {} | code={} | status={} | msg={} | data={}",
            request.method,
            request.url.path,
            exc.code,
            exc.status_code,
            exc.msg,
            exc.data,
        )
        # 生产环境不外泄 data（可能含 SQL 字段、约束名等内部细节）
        expose_data = exc.data if settings.ENVIRONMENT != EnvironmentEnum.PROD else None
        return ErrorResponse(msg=exc.msg, code=exc.code, status_code=exc.status_code, data=expose_data)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.error(
            "[HTTP异常] {} {} | status_code={} | detail={}",
            request.method,
            request.url.path,
            exc.status_code,
            exc.detail,
        )
        return ErrorResponse(msg=exc.detail, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        msg = errors[0].get("msg", str(errors[0])) if errors else "请求参数验证失败"
        if msg.startswith("Value error"):
            msg = msg[11:].lstrip(" ,")
        logger.error(
            "[参数验证异常] {} {} | errors={}",
            request.method,
            request.url.path,
            errors,
        )
        return ErrorResponse(msg=str(msg), status_code=_HTTP_422, data=errors)

    @app.exception_handler(ResponseValidationError)
    async def response_validation_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
        logger.error(
            "[响应验证异常] {} {} | errors={}",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return ErrorResponse(msg="服务器响应格式错误", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, data=exc.body)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """数据库异常统一出口。

        分类（t19）：
        - ``IntegrityError``：约束类问题，按具体原因给出可操作文案（409 等）；
        - 其它：**不再返回 400**（把服务端故障说成客户端的错会让监控失明），
          连接类（InterfaceError/DisconnectionError/连接中断文案）→ 503，其余 → 500；
        - 文案不再拼 ``exc_type``/驱动原文，细节只进日志（``logger.opt(exception=...)`` 带堆栈）。
        """
        if isinstance(exc, IntegrityError):
            detail = str(exc.orig) if exc.orig else str(exc)
            expose_detail = detail if settings.ENVIRONMENT != EnvironmentEnum.PROD else None
            logger.opt(exception=exc).error("[数据库异常] {} {}", request.method, request.url.path)
            if _is_connection_detail(detail):
                return ErrorResponse(msg="数据库连接失败", status_code=status.HTTP_503_SERVICE_UNAVAILABLE, data=expose_detail)
            if "Duplicate entry" in detail:
                return ErrorResponse(msg="数据重复，请检查唯一字段", status_code=status.HTTP_409_CONFLICT, data=expose_detail)
            if "foreign key constraint" in detail:
                return ErrorResponse(msg="存在关联数据，无法删除", status_code=status.HTTP_409_CONFLICT, data=expose_detail)
            if "cannot be null" in detail:
                return ErrorResponse(msg="必填字段缺失", status_code=status.HTTP_409_CONFLICT, data=expose_detail)
            return ErrorResponse(msg="数据已存在或违反完整性约束", status_code=status.HTTP_409_CONFLICT, data=expose_detail)

        detail = str(getattr(exc, "orig", None) or exc)
        logger.opt(exception=exc).error("[数据库异常] {} {}", request.method, request.url.path)
        if isinstance(exc, (InterfaceError, DisconnectionError)) or _is_connection_detail(detail):
            return ErrorResponse(msg="数据库连接失败", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return ErrorResponse(msg="数据库操作失败", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @app.exception_handler(ValueError)
    async def value_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.error("[值异常] {} {} | msg={}", request.method, request.url.path, exc)
        return ErrorResponse(msg=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.opt(exception=exc).error(
            "[未捕获异常] {} {} | type={} | detail={}",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc,
        )
        # 细节只进日志/堆栈：客户端只得到通用文案（生产不回显内部信息）
        return ErrorResponse(msg="服务器内部错误", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
