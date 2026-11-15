import json
import uuid
from typing import Any

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.common.enums import RedisInitKeyConfig, SysParamKey
from app.common.response import ErrorResponse
from app.config.setting import settings
from app.core.exceptions import CustomException
from app.core.logger import logger, reset_correlation_id, set_correlation_id
from app.core.redis_crud import RedisCURD
from app.utils.ip_local_util import get_client_ip


class CustomCORSMiddleware(CORSMiddleware):
    """CORS 中间件"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(
            app,
            allow_origins=settings.ALLOW_ORIGINS,
            allow_methods=settings.ALLOW_METHODS,
            allow_headers=settings.ALLOW_HEADERS,
            allow_credentials=settings.ALLOW_CREDENTIALS,
            expose_headers=settings.CORS_EXPOSE_HEADERS,
        )


class RequestLogMiddleware(BaseHTTPMiddleware):
    """演示模式 & IP黑名单拦截"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = get_client_ip(request)

        try:
            path = request.url.path
            config = await self._load_config(request)
            is_blacklisted = bool(client_ip and client_ip in config[SysParamKey.IP_BLACK_LIST])
            in_demo = (
                config.get(SysParamKey.DEMO_ENABLE, False)
                and request.method != "GET"
                and (client_ip is None or client_ip not in config.get(SysParamKey.IP_WHITE_LIST, ()))
                and not any(
                    path.startswith(item.rstrip("*")) if item.endswith("*") else path == item
                    for item in settings.WHITE_API_LIST_PATH
                    if isinstance(item, str) and item
                )
            )

            if is_blacklisted or in_demo:
                logger.warning(
                    "请求被拦截: {} {} | ip={} | 原因={}",
                    request.method,
                    path,
                    client_ip,
                    "IP黑名单" if is_blacklisted else "演示模式",
                )
                return ErrorResponse(msg="IP已被黑名单" if is_blacklisted else "演示环境，禁止操作")

            return await call_next(request)
        except CustomException as e:
            logger.exception(f"中间件异常: {e!s}")
            return ErrorResponse(msg="系统异常，请联系管理员", data=str(e))

    @staticmethod
    async def _load_config(request: Request) -> dict:
        """加载中间件配置，失败时返回全部默认值。"""
        redis = getattr(request.app.state, "redis", None)
        if not redis:
            return {SysParamKey.DEMO_ENABLE: False, SysParamKey.IP_WHITE_LIST: (), SysParamKey.IP_BLACK_LIST: ()}
        try:
            config_keys = [
                f"{RedisInitKeyConfig.SYSTEM_CONFIG.key}:{SysParamKey.DEMO_ENABLE.value}",
                f"{RedisInitKeyConfig.SYSTEM_CONFIG.key}:{SysParamKey.IP_WHITE_LIST.value}",
                f"{RedisInitKeyConfig.SYSTEM_CONFIG.key}:{SysParamKey.IP_BLACK_LIST.value}",
            ]
            config_values = await RedisCURD(redis).mget(config_keys)
            result: dict[str, Any] = {SysParamKey.DEMO_ENABLE: False, SysParamKey.IP_WHITE_LIST: (), SysParamKey.IP_BLACK_LIST: ()}
            raw_demo, raw_white, raw_black = config_values
            for raw, key in ((raw_demo, SysParamKey.DEMO_ENABLE), (raw_white, SysParamKey.IP_WHITE_LIST), (raw_black, SysParamKey.IP_BLACK_LIST)):
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    logger.error("解析系统配置 %s 失败", key)
                    continue
                if not isinstance(payload, dict) or payload.get("status", 0) != 0:
                    continue
                cv = payload.get("config_value")
                if cv is None:
                    continue
                if key == SysParamKey.DEMO_ENABLE:
                    result[key.value] = cv in (True, "true", "1", "yes", "on")
                else:
                    result[key.value] = json.loads(cv) if isinstance(cv, str) else cv
            return result
        except Exception:
            return {SysParamKey.DEMO_ENABLE: False, SysParamKey.IP_WHITE_LIST: (), SysParamKey.IP_BLACK_LIST: ()}


class CustomGZipMiddleware(GZipMiddleware):
    """GZip 压缩中间件"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app, minimum_size=settings.GZIP_MIN_SIZE, compresslevel=settings.GZIP_COMPRESS_LEVEL)


class CustomHTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """HTTP → HTTPS 重定向中间件（信任前端代理的 X-Forwarded-Proto 头）"""

    async def dispatch(self, request: Request, call_next):
        if request.url.scheme != "https" and request.headers.get("X-Forwarded-Proto") != "https":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url, 301)
        return await call_next(request)


def host_of(value: str) -> str:
    """从 Host 头里取出主机部分（小写、去端口）。

    修正 Starlette 的 ``host.split(":")[0]`` 在 IPv6 下的误判：
    ``127.0.0.1:8000`` → ``127.0.0.1``；``[::1]:8000`` → ``::1``；裸 ``::1`` → ``::1``。
    """
    v = (value or "").strip().lower()
    if v.startswith("["):
        end = v.find("]")
        return v[1:end] if end != -1 else v
    # 只有「主机:端口」这一种情况该剥；裸 IPv6 里的多个冒号不是端口分隔符
    return v.rsplit(":", 1)[0] if v.count(":") == 1 else v


class CustomTrustedHostMiddleware:
    """可信主机 Host 头校验中间件（纯 ASGI 实现）。

    在 Starlette ``TrustedHostMiddleware`` 基础上修正两处，并保持其余语义不变：
    1. **IPv6 字面量**：Starlette 用 ``host.split(":")[0]``，``[::1]:8000`` 会被切成 ``"["``，
       导致 ``::1`` 永远校验失败（本地开 ``ALLOW_LOCALHOST_HOSTS`` 时用 IPv6 访问会 400）；
    2. **大小写**：DNS 主机名不区分大小写，主机与允许清单统一转小写后比较。

    其余行为照旧：``*`` 放行全部；支持 ``*.example.com`` 形式通配；``www.`` 前缀可 301 重定向；
    允许清单里的条目也做同样归一（``[::1]`` 与 ``[::1]:8000`` 都按 ``::1`` 处理）。
    """

    app: ASGIApp
    allowed_hosts: list[str]
    allow_any: bool
    www_redirect: bool

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: list[str] | None = None,
        www_redirect: bool = True,
    ) -> None:
        hosts = allowed_hosts if allowed_hosts is not None else settings.ALLOWED_HOSTS
        normalized: list[str] = []
        for pattern in hosts:
            assert "*" not in pattern[1:], "通配符只允许出现在最左侧（如 *.example.com）"
            if pattern.startswith("*") and pattern != "*":
                assert pattern.startswith("*."), "通配符只允许 *.example.com 形式"
            normalized.append(host_of(pattern))
        self.app = app
        self.allowed_hosts = normalized
        self.allow_any = "*" in normalized
        self.www_redirect = www_redirect

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.allow_any or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        host = host_of(Headers(scope=scope).get("host", ""))
        found_www_redirect = False
        for pattern in self.allowed_hosts:
            if host == pattern or (pattern.startswith("*") and host.endswith(pattern[1:])):
                await self.app(scope, receive, send)
                return
            if "www." + host == pattern:
                found_www_redirect = True

        if scope["type"] == "websocket":
            # WS 上不能发 HTTP 响应：按「策略违规」关闭连接
            await send({"type": "websocket.close", "code": 1008})
            return
        response: Response
        if found_www_redirect and self.www_redirect:
            url = f"{scope.get('scheme', 'http')}://www.{host}"
            path = scope.get("path", "/")
            query = scope.get("query_string", b"").decode()
            response = RedirectResponse(f"{url}{path}" + (f"?{query}" if query else ""), 301)
        else:
            response = PlainTextResponse("Invalid host header", 400)
        await response(scope, receive, send)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件"""

    def __init__(self, app: ASGIApp) -> None:
        self._header = "X-Correlation-ID"
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(self._header) or str(uuid.uuid4())
        token = set_correlation_id(cid)
        try:
            response = await call_next(request)
            response.headers[self._header] = cid
            return response
        finally:
            reset_correlation_id(token)

