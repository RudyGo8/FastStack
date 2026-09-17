from types import SimpleNamespace

from app.modules.system.auth.service import LoginService


def test_collect_permissions_ignores_soft_deleted_menus() -> None:
    active = SimpleNamespace(
        id=11,
        status=0,
        is_deleted=False,
        permission="module_sop:chat:query",
    )
    deleted = SimpleNamespace(
        id=12,
        status=0,
        is_deleted=True,
        permission="module_ai:chat:query",
    )
    role = SimpleNamespace(status=0, menus=[active, deleted])
    user = SimpleNamespace(is_superuser=False, roles=[role])

    permissions, menu_ids = LoginService._collect_permissions(user)

    assert permissions == ["module_sop:chat:query"]
    assert menu_ids == [11]
