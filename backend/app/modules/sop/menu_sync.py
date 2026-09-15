"""S&OP 菜单的声明式增量同步，支持角色差异化授权。

角色定义（来自 sys_role 表）：
- SUPER_ADMIN (id=1): 全部菜单
- ADMIN (id=2): 全部菜单
- USER (id=3): 业务页面 + AI 问答 + 数据中心业务数据（只读）
"""

from dataclasses import dataclass, field

from app.modules.system.menu.model import MenuModel
from app.modules.system.role.model import RoleMenusModel, RoleModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

# 角色代码常量（对应 sys_role.code）
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_USER = "USER"
ADMIN_ROLE_CODES = {ROLE_SUPER_ADMIN, ROLE_ADMIN}


@dataclass(frozen=True, slots=True)
class SopMenuDefinition:
    """不依赖数据库自增 ID 的 S&OP 菜单定义。

    admin_only=True 的菜单仅管理员可见，普通用户不可见。
    """

    key: str
    name: str
    type: int
    order: int
    permission: str | None = None
    route_name: str | None = None
    route_path: str | None = None
    component_path: str | None = None
    icon: str | None = None
    redirect: str | None = None
    description: str | None = None
    admin_only: bool = False
    children: tuple["SopMenuDefinition", ...] = ()


def _button(
    key: str,
    name: str,
    order: int,
    permission: str,
    description: str,
    admin_only: bool = False,
) -> SopMenuDefinition:
    return SopMenuDefinition(
        key=key,
        name=name,
        type=3,
        order=order,
        permission=permission,
        description=description,
        admin_only=admin_only,
    )


# ─── S&OP 分析 ────────────────────────────────────────────────────────────────
# 设计文档：普通用户和管理员共用，含工作台/预测校验/市场信息/会议报告。
SOP_ANALYSIS_GROUP = SopMenuDefinition(
    key="sop-analysis",
    name="S&OP 分析",
    type=1,
    order=1,
    route_name="SopAnalysis",
    route_path="/sop-analysis",
    icon="ri:line-chart-line",
    redirect="/sop-analysis/workspace",
    description="S&OP 产销协同智能分析",
    children=(
        SopMenuDefinition(
            key="workspace",
            name="工作台",
            type=2,
            order=1,
            permission="module_sop:data:query",
            route_name="SopWorkspace",
            route_path="workspace",
            component_path="module_sop/dashboard/index",
            icon="ri:dashboard-3-line",
            description="计划工作台",
        ),
        SopMenuDefinition(
            key="forecast-validation",
            name="预测校验",
            type=2,
            order=2,
            permission="module_sop:report:query",
            route_name="SopForecastValidation",
            route_path="forecast-validation",
            component_path="module_sop/analysis/index",
            icon="ri:analytics-line",
            description="预测校验",
        ),
        SopMenuDefinition(
            key="supply-demand",
            name="市场信息",
            type=2,
            order=3,
            permission="module_sop:data:query",
            route_name="SopSupplyDemand",
            route_path="supply-demand",
            component_path="module_sop/market/index",
            icon="ri:fire-line",
            description="市场信息",
        ),
        SopMenuDefinition(
            key="meeting-report",
            name="会议报告",
            type=2,
            order=4,
            permission="module_sop:report:query",
            route_name="SopMeetingReport",
            route_path="meeting-report",
            component_path="module_sop/report/index",
            icon="ri:file-chart-line",
            description="会议报告",
            children=(
                _button(
                    "report-generate",
                    "生成快照",
                    1,
                    "module_sop:report:generate",
                    "手动触发数据快照",
                    admin_only=True,
                ),
                _button(
                    "report-export",
                    "导出报告",
                    2,
                    "module_sop:report:export",
                    "导出 Word 会议报告",
                ),
            ),
        ),
    ),
)


# ─── 数据中心 ─────────────────────────────────────────────────────────────────
# 设计文档：业务数据（只读）全员可见；数据质量/数据导入/数据源仅管理员。
DATA_CENTER_GROUP = SopMenuDefinition(
    key="data-center",
    name="数据中心",
    type=1,
    order=2,
    route_name="DataCenter",
    route_path="/data-center",
    icon="ri:database-2-line",
    redirect="/data-center/business-data",
    description="业务数据与数据治理",
    children=(
        SopMenuDefinition(
            key="business-data",
            name="业务数据",
            type=2,
            order=1,
            permission="module_sop:data:query",
            route_name="BusinessData",
            route_path="business-data",
            component_path="module_sop/data_center/index",
            icon="ri:line-chart-line",
            description="业务数据（只读）",
        ),
        SopMenuDefinition(
            key="data-quality",
            name="数据质量",
            type=2,
            order=2,
            permission="module_sop:data:import",
            route_name="DataQuality",
            route_path="data-quality",
            component_path="module_sop/data_center/index",
            icon="ri:shield-check-line",
            description="数据质量",
            admin_only=True,
        ),
        SopMenuDefinition(
            key="data-import",
            name="数据导入",
            type=2,
            order=3,
            permission="module_sop:data:import",
            route_name="DataImport",
            route_path="data-import",
            component_path="module_sop/data_center/index",
            icon="ri:upload-2-line",
            description="数据导入",
            admin_only=True,
        ),
        SopMenuDefinition(
            key="data-source",
            name="数据源",
            type=2,
            order=4,
            permission="module_sop:data:sync",
            route_name="DataSource",
            route_path="data-source",
            component_path="module_sop/data_center/index",
            icon="ri:server-line",
            description="数据源配置",
            admin_only=True,
        ),
    ),
)


# ─── AI 助手 ─────────────────────────────────────────────────────────────────
# 设计文档：智能问答/会话记录全员；知识库管理/模型配置/Prompt配置仅管理员。
AI_ASSISTANT_GROUP = SopMenuDefinition(
    key="ai-assistant",
    name="AI 助手",
    type=1,
    order=3,
    route_name="AiAssistant",
    route_path="/ai-assistant",
    icon="ri:robot-line",
    redirect="/ai-assistant/chat",
    description="AI 智能对话与知识库管理",
    children=(
        SopMenuDefinition(
            key="ai-chat",
            name="智能问答",
            type=2,
            order=1,
            route_name="AiChat",
            route_path="chat",
            component_path="module_ai/chat/index",
            icon="ri:chat-smile-3-line",
            description="AI 对话与 SOP 知识问答",
        ),
        SopMenuDefinition(
            key="ai-memory",
            name="会话记录",
            type=2,
            order=2,
            permission="module_ai:chat:query",
            route_name="AiMemory",
            route_path="memory",
            component_path="module_ai/memory/index",
            icon="ri:history-line",
            description="AI 会话历史记录",
        ),
        SopMenuDefinition(
            key="ai-knowledge",
            name="知识库管理",
            type=2,
            order=3,
            permission="module_sop:document:query",
            route_name="AiKnowledge",
            route_path="knowledge",
            component_path="module_ai/knowledge/index",
            icon="ri:book-open-line",
            description="知识库文档管理",
            admin_only=True,
            children=(
                _button(
                    "document-upload",
                    "文档上传",
                    1,
                    "module_sop:document:upload",
                    "上传文档解析入向量库",
                    admin_only=True,
                ),
                _button(
                    "document-delete",
                    "文档删除",
                    2,
                    "module_sop:document:delete",
                    "删除文档向量数据",
                    admin_only=True,
                ),
            ),
        ),
        SopMenuDefinition(
            key="ai-model",
            name="模型配置",
            type=2,
            order=4,
            permission="module_ai:model:config",
            route_name="AiModel",
            route_path="model",
            component_path="module_ai/model/index",
            icon="ri:settings-4-line",
            description="模型配置",
            admin_only=True,
        ),
        SopMenuDefinition(
            key="ai-prompt",
            name="Prompt 配置",
            type=2,
            order=5,
            permission="module_ai:prompt:config",
            route_name="AiPrompt",
            route_path="prompt",
            component_path="module_ai/prompt/index",
            icon="ri:code-s-slash-line",
            description="Prompt 配置",
            admin_only=True,
        ),
    ),
)


# 合并为完整菜单树（系统管理/监控管理等由 sys_menu.json 种子维护，此处不重复声明）
SOP_MENU_TREE: tuple[SopMenuDefinition, ...] = (
    SOP_ANALYSIS_GROUP,
    DATA_CENTER_GROUP,
)

AI_MENU_TREE: tuple[SopMenuDefinition, ...] = (AI_ASSISTANT_GROUP,)


# 菜单重组前遗留的旧分组根，reconcile 时软删除。
# 仅包含被替换的旧顶级 route_name，新分组/子菜单的 route_name 不能在此列表中。
RETIRED_ROOT_ROUTE_NAMES: tuple[str, ...] = (
    "Sop",  # 旧 S&OP 顶级菜单（已改为 SopAnalysis 分组）
    "Ai",  # 旧 AI 管理顶级菜单（已改为 AiAssistant 分组）
    "SopDashboard",
    "SopMarket",
    "SopReport",
    "SopDataCenter",  # 旧扁平顶级菜单（已改为子菜单）
)


async def _find_menu(
    db: AsyncSession, definition: SopMenuDefinition, parent_id: int | None
) -> MenuModel | None:
    if definition.route_name:
        menu = await db.scalar(
            select(MenuModel).where(
                MenuModel.route_name == definition.route_name,
                MenuModel.is_deleted.is_(False),
            )
        )
        if menu is not None:
            return menu
    if definition.type == 3 and definition.permission:
        menu = await db.scalar(
            select(MenuModel).where(
                MenuModel.type == 3,
                MenuModel.permission == definition.permission,
                MenuModel.is_deleted.is_(False),
            )
        )
        if menu is not None:
            return menu
    return await db.scalar(
        select(MenuModel).where(
            MenuModel.parent_id == parent_id,
            MenuModel.type == definition.type,
            MenuModel.name == definition.name,
            MenuModel.is_deleted.is_(False),
        )
    )


async def _upsert_tree(
    db: AsyncSession,
    definitions: tuple[SopMenuDefinition, ...],
    parent_id: int | None,
    menu_ids: set[int],
) -> None:
    for definition in definitions:
        menu = await _find_menu(db, definition, parent_id)
        if menu is None:
            menu = MenuModel(
                name=definition.name, type=definition.type, order=definition.order
            )
            db.add(menu)

        menu.name = definition.name
        menu.type = definition.type
        menu.order = definition.order
        menu.permission = definition.permission
        menu.route_name = definition.route_name
        menu.route_path = definition.route_path
        menu.component_path = definition.component_path
        menu.icon = definition.icon
        menu.redirect = definition.redirect
        menu.description = definition.description
        menu.parent_id = parent_id
        menu.status = 0
        menu.hidden = False
        menu.keep_alive = True
        menu.always_show = False
        menu.title = definition.name
        menu.scope = "web"
        menu.affix = False
        menu.link = None
        menu.is_iframe = False
        menu.is_hide_tab = False
        menu.active_path = None
        menu.show_badge = False
        menu.show_text_badge = None
        await db.flush()
        menu_ids.add(menu.id)
        await _upsert_tree(db, definition.children, menu.id, menu_ids)


async def grant_menus_by_role(
    db: AsyncSession, menu_ids_by_admin_only: dict[bool, set[int]]
) -> None:
    """按角色差异化授权：
    - USER: 仅绑定非 admin_only 的菜单
    - ADMIN / SUPER_ADMIN: 绑定全部菜单
    """
    if not any(menu_ids_by_admin_only.values()):
        return

    roles = await db.scalars(select(RoleModel).where(RoleModel.is_deleted.is_(False)))
    all_menu_ids = menu_ids_by_admin_only.get(True, set()) | menu_ids_by_admin_only.get(
        False, set()
    )
    existing = set(
        (
            await db.execute(
                select(RoleMenusModel.role_id, RoleMenusModel.menu_id).where(
                    RoleMenusModel.menu_id.in_(all_menu_ids)
                )
            )
        ).all()
    )

    inserts = []
    for role in roles:
        code = role.code or ""
        if code in ADMIN_ROLE_CODES:
            target_ids = all_menu_ids
        else:
            target_ids = menu_ids_by_admin_only.get(False, set())
        for menu_id in target_ids:
            if (role.id, menu_id) not in existing:
                inserts.append(RoleMenusModel(role_id=role.id, menu_id=menu_id))

    if inserts:
        db.add_all(inserts)
    await db.flush()


async def _prune_children(db: AsyncSession, parent_id: int, keep_ids: set[int]) -> None:
    """软删除父节点下不在声明集合中的残留菜单及其角色绑定。"""
    children = (
        await db.scalars(
            select(MenuModel).where(
                MenuModel.parent_id == parent_id,
                MenuModel.is_deleted.is_(False),
            )
        )
    ).all()
    for menu in children:
        if menu.id in keep_ids:
            continue
        await _prune_children(db, menu.id, keep_ids)
        menu.is_deleted = True
        await db.execute(
            delete(RoleMenusModel).where(RoleMenusModel.menu_id == menu.id)
        )
    await db.flush()


async def _retire_roots(db: AsyncSession, route_names: tuple[str, ...]) -> None:
    """软删除重组前遗留的旧分组根及其角色绑定。"""
    for route_name in route_names:
        menu = await db.scalar(
            select(MenuModel).where(
                MenuModel.route_name == route_name,
                MenuModel.is_deleted.is_(False),
            )
        )
        if menu is None:
            continue
        menu.is_deleted = True
        await db.execute(
            delete(RoleMenusModel).where(RoleMenusModel.menu_id == menu.id)
        )
    await db.flush()


def _collect_menu_ids_by_admin_only(
    definitions: tuple[SopMenuDefinition, ...],
) -> dict[bool, set[int]]:
    """遍历树，收集所有菜单 ID（含 admin_only 标记）。"""
    result: dict[bool, set[int]] = {True: set(), False: set()}

    def walk(defs: tuple[SopMenuDefinition, ...]) -> None:
        for d in defs:
            result[d.admin_only].add(d)
            walk(d.children)

    walk(definitions)
    return result


async def _reconcile_tree(
    db: AsyncSession,
    tree: tuple[SopMenuDefinition, ...],
    retired_roots: tuple[str, ...] = (),
) -> dict[bool, set[int]]:
    """upsert 声明树、清理残留与退役根，返回按 admin_only 分组的菜单 ID 集合。"""
    menu_ids: set[int] = set()
    admin_only_map: dict[int, bool] = {}

    async def upsert_with_admin_flag(
        defs: tuple[SopMenuDefinition, ...],
        parent_id: int | None,
    ) -> None:
        for definition in defs:
            menu = await _find_menu(db, definition, parent_id)
            if menu is None:
                menu = MenuModel(
                    name=definition.name, type=definition.type, order=definition.order
                )
                db.add(menu)

            menu.name = definition.name
            menu.type = definition.type
            menu.order = definition.order
            menu.permission = definition.permission
            menu.route_name = definition.route_name
            menu.route_path = definition.route_path
            menu.component_path = definition.component_path
            menu.icon = definition.icon
            menu.redirect = definition.redirect
            menu.description = definition.description
            menu.parent_id = parent_id
            menu.status = 0
            menu.hidden = False
            menu.keep_alive = True
            menu.always_show = False
            menu.title = definition.name
            menu.scope = "web"
            menu.affix = False
            menu.link = None
            menu.is_iframe = False
            menu.is_hide_tab = False
            menu.active_path = None
            menu.show_badge = False
            menu.show_text_badge = None
            await db.flush()
            menu_ids.add(menu.id)
            admin_only_map[menu.id] = definition.admin_only
            await upsert_with_admin_flag(definition.children, menu.id)

    await upsert_with_admin_flag(tree, None)

    # 清理残留子节点
    for root in tree:
        found = await _find_menu(db, root, None)
        if found is not None:
            await _prune_children(db, found.id, menu_ids)

    await _retire_roots(db, retired_roots)

    # 按 admin_only 分组
    result: dict[bool, set[int]] = {True: set(), False: set()}
    for mid, is_admin in admin_only_map.items():
        result[is_admin].add(mid)

    return result


async def reconcile_sop_menus(db: AsyncSession) -> dict[bool, set[int]]:
    """增量同步 S&OP 业务菜单（S&OP 分析 + 数据中心）并清理旧分组根。"""
    return await _reconcile_tree(db, SOP_MENU_TREE, RETIRED_ROOT_ROUTE_NAMES)


async def reconcile_ai_menus(db: AsyncSession) -> dict[bool, set[int]]:
    """增量同步 AI 助手菜单并清理旧分组根。"""
    return await _reconcile_tree(db, AI_MENU_TREE, RETIRED_ROOT_ROUTE_NAMES)


async def get_sop_menu_ids(db: AsyncSession) -> set[int]:
    """返回当前数据库中由声明管理的全部 SOP/AI 菜单 ID（含 admin_only）。

    用于 role/service.py 在更新角色菜单时，确保声明式管理的菜单始终被包含。
    """
    ids: set[int] = set()

    async def collect(
        defs: tuple[SopMenuDefinition, ...], parent_id: int | None
    ) -> None:
        for d in defs:
            menu = await _find_menu(db, d, parent_id)
            if menu is not None:
                ids.add(menu.id)
                await collect(d.children, menu.id)

    await collect(SOP_MENU_TREE, None)
    await collect(AI_MENU_TREE, None)
    return ids


async def grant_all_menus_by_role(
    db: AsyncSession, *results: dict[bool, set[int]]
) -> None:
    """合并多个菜单树的 admin_only 分组，统一按角色授权。"""
    merged: dict[bool, set[int]] = {True: set(), False: set()}
    for result in results:
        merged[True] |= result.get(True, set())
        merged[False] |= result.get(False, set())
    await grant_menus_by_role(db, merged)
