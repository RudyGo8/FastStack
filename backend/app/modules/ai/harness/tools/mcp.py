"""MCP 工具发现与调用：有界、可取消、按需启用。

未开启 ``AI_HARNESS_MCP_ENABLE`` 时始终返回空列表，普通项目不需要任何 MCP 服务。
"""

import asyncio
import json
from pathlib import Path
from time import perf_counter

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config.setting import settings
from app.core.logger import logger
from app.modules.ai.harness.tracing import record_mcp_call

DEFAULT_CONFIG = Path(__file__).with_name("mcp_servers.json")


def _config_path() -> Path:
    configured = (settings.AI_HARNESS_MCP_CONFIG or "").strip()
    return Path(configured) if configured else DEFAULT_CONFIG


def _load_servers() -> dict:
    path = _config_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", data)
    return servers if isinstance(servers, dict) else {}


class MCPClientManager:
    def __init__(self):
        self._tools: list = []
        self._initialized = False
        self._lock = asyncio.Lock()
        self._capacity = asyncio.Semaphore(settings.AI_HARNESS_TOOL_MAX_CONCURRENCY)

    @property
    def _enabled(self) -> bool:
        return settings.AI_HARNESS_ENABLE and settings.AI_HARNESS_MCP_ENABLE

    async def _load_server(self, name: str, server_cfg: dict) -> list:
        try:
            async with asyncio.timeout(settings.AI_HARNESS_TOOL_TIMEOUT_SECONDS), self._capacity:
                client = MultiServerMCPClient({name: server_cfg}, tool_interceptors=[self._call_tool])
                tools = await client.get_tools()
                logger.info(f"MCP 服务已加载 name={name} 工具数={len(tools)}")
                return tools
        except Exception as exc:
            logger.warning(f"MCP 服务加载失败 name={name} 错误类型={type(exc).__name__}")
            return []

    async def _call_tool(self, request, handler):
        started = perf_counter()
        call = {"server_name": request.server_name, "tool_name": request.name, "success": False}
        try:
            async with asyncio.timeout(settings.AI_HARNESS_TOOL_TIMEOUT_SECONDS), self._capacity:
                result = await handler(request)
            call["success"] = not getattr(result, "isError", False) and getattr(result, "status", None) != "error"
            return result
        except (Exception, asyncio.CancelledError) as exc:
            call["error_type"] = type(exc).__name__
            raise
        finally:
            call["duration_ms"] = round((perf_counter() - started) * 1000, 2)
            record_mcp_call(call)

    async def initialize(self, *, force: bool = False) -> None:
        async with self._lock:
            if not self._enabled:
                self._tools = []
                self._initialized = False
                return
            if self._initialized and not force:
                return
            servers = await asyncio.to_thread(_load_servers)
            if not servers:
                self._tools = []
                self._initialized = True
                return
            async with asyncio.TaskGroup() as group:
                tasks = [group.create_task(self._load_server(name, cfg)) for name, cfg in servers.items()]
            # 全部发现完成后原子发布；中途取消仍可重试。
            self._tools = [tool for task in tasks for tool in task.result()]
            self._initialized = True
            logger.info(f"MCP 工具加载完成 count={len(self._tools)}")

    async def reload(self) -> list:
        await self.initialize(force=True)
        return list(self._tools)

    async def get_agent_tools(self) -> list:
        if not self._enabled:
            return []
        await self.initialize()
        return list(self._tools)


mcp_client_manager = MCPClientManager()
