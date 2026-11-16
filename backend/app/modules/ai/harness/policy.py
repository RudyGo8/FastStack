"""任务恢复时的身份重载：从系统库重新收集权限，不信任任务中保存的快照。"""

from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_db_session
from app.modules.ai.harness.contracts import Principal
from app.modules.system.auth.service import LoginService
from app.modules.system.role.model import RoleModel
from app.modules.system.user.model import UserModel


async def load_principal(user_id: int) -> Principal:
    """按用户 ID 重新计算权限；用户删除/停用或不存在时拒绝执行。"""
    async with async_db_session() as session:
        result = await session.execute(
            select(UserModel)
            .where(UserModel.id == user_id, UserModel.is_deleted.is_(False), UserModel.status == 0)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.menus))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise PermissionError("执行用户已删除、停用或不存在")
        # 登录收集器已处理菜单停用/删除；此处同时排除已删除角色。
        permission_user = SimpleNamespace(
            is_superuser=user.is_superuser,
            roles=[role for role in user.roles if not role.is_deleted],
        )
        permissions, _ = LoginService._collect_permissions(permission_user)
        return Principal(user.id, user.username, frozenset(permissions), user.is_superuser)
