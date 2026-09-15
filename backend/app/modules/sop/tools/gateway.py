from app.modules.sop.tools.mcp_gateway.client_manager import mcp_client_manager
from app.modules.sop.tools.registry import TOOL_REGISTRY


# 工具网关-统一入口
class ToolGateway:
    def __init__(self, registry, mcp_manager):
        self._registry = registry
        self._mcp = mcp_manager

    async def get_tools(self, allowed_local: set[str] | None = None, include_mcp: bool = True):
        local = [spec.tool for name, spec in self._registry.items() if allowed_local is None or name in allowed_local]
        mcp = await self._mcp.get_agent_tools() if include_mcp else []
        return local + mcp

    async def get_mcp_tool_names(self):
        tools = await self._mcp.get_agent_tools()
        # 字典推导式：安全获取属性
        return {getattr(t, "name", "").strip() for t in tools if getattr(t, "name", None)}


tool_gateway = ToolGateway(TOOL_REGISTRY, mcp_client_manager)
