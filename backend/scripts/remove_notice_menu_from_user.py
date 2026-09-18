"""移除普通用户角色的公告管理菜单权限（使用原始 SQL 避免模型依赖问题）"""
import asyncio

import aiomysql

from app.config.setting import settings


async def main():
    pool = await aiomysql.create_pool(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        db=settings.DATABASE_NAME,
        charset="utf8mb4",
        autocommit=True,
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 找普通用户角色 ID
            await cur.execute('SELECT id FROM sys_role WHERE code = "USER" AND is_deleted = 0')
            role_row = await cur.fetchone()
            if not role_row:
                print("❌ 未找到普通用户角色")
                return
            role_id = role_row[0]

            # 找公告管理菜单 ID
            await cur.execute(
                'SELECT id FROM sys_menu WHERE permission = "module_system:notice:query" AND is_deleted = 0'
            )
            menu_row = await cur.fetchone()
            if not menu_row:
                print("❌ 未找到公告管理菜单")
                return
            menu_id = menu_row[0]

            # 删除关联
            await cur.execute(
                "DELETE FROM sys_role_menus WHERE role_id = %s AND menu_id = %s",
                (role_id, menu_id),
            )
            print(f"✅ 已移除普通用户的公告管理菜单 (role_id={role_id}, menu_id={menu_id}, 影响 {cur.rowcount} 行)")

    pool.close()
    await pool.wait_closed()


asyncio.run(main())
