"""S&OP 菜单增量同步与全角色授权回归测试。"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.modules.sop.menu_sync import reconcile_sop_menus
from app.modules.system.menu.model import MenuModel
from app.modules.system.role.model import RoleMenusModel, RoleModel
from app.modules.system.role.schema import RoleCreateSchema
from app.modules.system.role.service import RoleService


async def test_reconcile_sop_menus_is_idempotent_and_grants_all_roles(test_client: TestClient) -> None:
    """捕获存量库跳过菜单种子、固定菜单 ID 导致角色未授权的问题。"""
    _ = test_client
    async with async_db_session() as db, db.begin():
        unrelated = MenuModel(name="回归测试保留菜单", type=2, route_name="SopSyncKeepMe", route_path="/sop-sync-keep")
        role = RoleModel(name="SOP 回归测试角色", code="SOP_SYNC_TEST", order=999, status=0, data_scope=1)
        db.add_all([unrelated, role])
        await db.flush()
        unrelated_id = unrelated.id
        role_id = role.id

        first = await reconcile_sop_menus(db)
        second = await reconcile_sop_menus(db)

        assert first == second
        assert len(first) == 16
        assert await db.scalar(select(func.count()).select_from(MenuModel).where(MenuModel.id == unrelated_id)) == 1

        links = (
            await db.scalars(
                select(RoleMenusModel.menu_id).where(
                    RoleMenusModel.role_id == role_id,
                    RoleMenusModel.menu_id.in_(first),
                )
            )
        ).all()
        assert set(links) == first
        assert len(links) == len(set(links))

        root = await db.scalar(select(MenuModel).where(MenuModel.route_name == "Sop"))
        dashboard = await db.scalar(select(MenuModel).where(MenuModel.route_name == "SopDashboard"))
        assert root is not None
        assert dashboard is not None
        assert dashboard.parent_id == root.id

        await db.rollback()


async def test_setting_role_permissions_cannot_remove_sop(test_client: TestClient) -> None:
    """捕获角色授权采用全量替换时误删全用户必选 S&OP 权限的问题。"""
    _ = test_client
    async with async_db_session() as db, db.begin():
        role = RoleModel(name="SOP 受限回归角色", code="SOP_LIMITED_TEST", order=998, status=0, data_scope=1)
        db.add(role)
        await db.flush()
        sop_ids = await reconcile_sop_menus(db)

        await RoleService(AuthSchema(), db)._set_role_menus([role.id], [])

        remaining = set(
            (
                await db.scalars(
                    select(RoleMenusModel.menu_id).where(
                        RoleMenusModel.role_id == role.id,
                        RoleMenusModel.menu_id.in_(sop_ids),
                    )
                )
            ).all()
        )
        assert remaining == sop_ids
        await db.rollback()


async def test_new_role_receives_all_sop_menus(test_client: TestClient) -> None:
    """捕获应用启动后新建角色没有 S&OP 权限的问题。"""
    _ = test_client
    async with async_db_session() as db, db.begin():
        sop_ids = await reconcile_sop_menus(db)
        role = await RoleService(AuthSchema(), db).create(
            RoleCreateSchema(name="SOP 新建回归角色", code="SOP_NEW_TEST", order=997, data_scope=1)
        )

        granted = set(
            (await db.scalars(select(RoleMenusModel.menu_id).where(RoleMenusModel.role_id == role.id))).all()
        )
        assert sop_ids <= granted
        await db.rollback()
