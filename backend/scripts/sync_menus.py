"""执行菜单同步脚本。"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import pkgutil
import importlib

logging.disable(logging.CRITICAL)

def import_models():
    import app.modules as mods
    for m in pkgutil.walk_packages(mods.__path__, prefix="app.modules."):
        if m.name.endswith(".model"):
            try:
                importlib.import_module(m.name)
            except Exception:
                pass

async def main():
    import_models()
    from sqlalchemy import text
    from app.core.database import async_db_session
    from app.modules.sop.menu_sync import (
        reconcile_sop_menus,
        reconcile_ai_menus,
        grant_all_menus_by_role,
    )

    async with async_db_session() as db:
        sop_result = await reconcile_sop_menus(db)
        ai_result = await reconcile_ai_menus(db)
        await grant_all_menus_by_role(db, sop_result, ai_result)
        await db.commit()

        sop_all = sop_result[True] | sop_result[False]
        ai_all = ai_result[True] | ai_result[False]
        print(f"✅ SOP 菜单同步完成: {len(sop_all)} 节点 (管理员专属: {len(sop_result[True])})")
        print(f"✅ AI 菜单同步完成: {len(ai_all)} 节点 (管理员专属: {len(ai_result[True])})")

        # 验证最终菜单结构
        sql = "SELECT id, parent_id, name, type, route_name, route_path FROM sys_menu WHERE is_deleted=0 AND parent_id IS NULL ORDER BY `order`, id"
        menus = (await db.execute(text(sql))).all()
        print("\n=== 顶级菜单 ===")
        for m in menus:
            print(f"  id={m[0]} {m[2]} → {m[4]} /{m[5]}")

        # 验证子菜单
        sql2 = "SELECT id, parent_id, name, type, route_name FROM sys_menu WHERE is_deleted=0 AND parent_id IS NOT NULL ORDER BY parent_id, `order`, id"
        children = (await db.execute(text(sql2))).all()
        print("\n=== 子菜单 ===")
        for m in children:
            print(f"  parent={m[1]} id={m[0]} type={m[3]} {m[2]} → {m[4]}")

        # 验证角色绑定
        sql3 = "SELECT r.name, COUNT(rm.menu_id) FROM sys_role r LEFT JOIN sys_role_menus rm ON r.id = rm.role_id WHERE r.is_deleted=0 GROUP BY r.id, r.name ORDER BY r.id"
        bindings = (await db.execute(text(sql3))).all()
        print("\n=== 角色菜单绑定统计 ===")
        for b in bindings:
            print(f"  {b[0]}: {b[1]} 个菜单")

asyncio.run(main())
