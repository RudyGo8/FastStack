"""按需导入重型 SDK 的小工具（首次属性访问时才真正 import）。

为什么需要：存储适配器在 import 期就把 boto3 / botocore / qcloud_cos / obs / paramiko /
alibabacloud_oss_v2 全部拉进来，而适配器工厂为了「零改工厂新增协议」会在导入时引入全部适配器 ——
于是每次冷启动都白付这段导入时间（本仓库实测：导入工厂 913ms、6 个重型 SDK 全部进入 sys.modules），
哪怕这次只用一个 SFTP 节点。

做法：模块级用代理对象占位，属性访问（如 ``boto3.client(...)``）时才 import 并缓存。
所以各适配器里的调用写法基本不用改，只是 import 时机从「启动」挪到「首次用到该协议」。

注意（踩过才知道）：
1. **函数签名上的注解会在 def 时就求值**（如 ``-> paramiko.SFTPClient``），所以模块要加
   ``from __future__ import annotations``，让注解变成字符串不求值；
2. ``from X import Y`` 是 import 语句、拿不到代理的好处：要么改成 ``mod.Y``，要么在真正用到的
   函数里局部 import；``except`` 子句里的异常类用 :func:`sdk_exception`（``except`` 表达式在
   异常发生时才求值，不会在导入期拉起 SDK）；
3. 类型检查器/IDE 需要真模块：用 ``if TYPE_CHECKING:`` 分支放真 import，``else`` 分支放代理，
   否则注解里把 ``Any`` 当类型用会触发 pyright ``reportInvalidTypeForm``，整条链退化为 Any。

验证：导入工厂后，这些重型 SDK 不应出现在 ``sys.modules``；构造对应协议客户端后才应出现。
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any, ClassVar, cast, override


class LazyModule:
    """模块代理：首次属性访问时才 import 真实模块，之后缓存复用。"""

    __slots__: ClassVar[tuple[str, ...]] = ("_module", "_name")

    def __init__(self, name: str) -> None:
        self._name: str = name
        self._module: ModuleType | None = None

    def _load(self) -> ModuleType:
        if self._module is None:
            self._module = importlib.import_module(self._name)
        return self._module

    def __getattr__(self, item: str) -> Any:
        return getattr(self._load(), item)

    @override
    def __repr__(self) -> str:  # pragma: no cover - 仅为调试可读
        state = "已导入" if self._module is not None else "未导入"
        return f"<LazyModule {self._name}（{state}）>"


def lazy_module(name: str) -> Any:
    """占位一个模块；类型上按 Any 用，避免到处写 cast（真实类型由 SDK 提供）。"""
    return LazyModule(name)


def sdk_exception(module_name: str, attr: str) -> type[BaseException]:
    """按需取 SDK 的异常类，专供 ``except`` 子句：

    .. code-block:: python

        except sdk_exception("botocore.exceptions", "ClientError") as exc:

    ``except`` 的表达式在**异常发生时才求值**，所以不会在导入期拉起 SDK；
    而 ``from X import Y`` 那种写法是 import 语句，拿不到代理的好处，只能这样换掉。
    """
    return cast(type[BaseException], getattr(importlib.import_module(module_name), attr))
