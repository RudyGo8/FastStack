"""SSH 运维服务：主机/片段 CRUD、连接探测、批量执行、终端建连。

安全：
- 凭据（密码/私钥/口令）Fernet 加密存储，出参永不返回；
- 批量执行与终端只允许「已启用」主机；
- 执行命令会记录审计日志（用户/主机/命令截断 200 字），不记录凭据。
"""

import asyncio
import io
import shlex
import time

import paramiko
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.crypto_util import CryptoUtil

from .crud import SshHostCRUD, SshSnippetCRUD
from .model import SshHostModel
from .schema import (
    BatchExecResultSchema,
    SshHostCreateSchema,
    SshHostOutSchema,
    SshHostTestSchema,
    SshHostUpdateSchema,
    SshSnippetCreateSchema,
    SshSnippetOutSchema,
    SshSnippetUpdateSchema,
)
from .terminal import TerminalManager

_CONNECT_TIMEOUT = 8
_MAX_CAPTURE = 4000
_BATCH_CONCURRENCY = 5


def _load_private_key(text: str | None, passphrase: str | None) -> paramiko.PKey:
    """解析私钥（支持 Ed25519 / RSA / ECDSA）。"""
    if not text:
        raise CustomException(msg="该主机未配置私钥")
    for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return key_cls.from_private_key(io.StringIO(text), password=passphrase or None)
        except paramiko.SSHException:
            continue
        except Exception:  # noqa: BLE001 - 口令错误等统一落到最终异常
            continue
    raise CustomException(msg="无法解析私钥（支持 Ed25519 / RSA / ECDSA）")


def connect_client(
    *,
    host: str,
    port: int,
    username: str,
    auth_type: str,
    password: str | None,
    private_key: str | None,
    passphrase: str | None,
) -> paramiko.SSHClient:
    """建立 SSH 连接（禁用 agent/默认密钥，只用显式凭据）。"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = _load_private_key(private_key, passphrase) if auth_type == "key" else None
    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=None if pkey is not None else (password or ""),
            pkey=pkey,
            timeout=_CONNECT_TIMEOUT,
            banner_timeout=_CONNECT_TIMEOUT,
            auth_timeout=_CONNECT_TIMEOUT,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception:
        client.close()
        raise
    return client


class SshHostService:
    """SSH 主机管理"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    def _crud(self) -> SshHostCRUD:
        return SshHostCRUD(self.auth, self.db)

    @staticmethod
    def _to_out(row: SshHostModel) -> SshHostOutSchema:
        out = SshHostOutSchema.model_validate(row)
        out.has_password = bool(row.password)
        out.has_private_key = bool(row.private_key)
        return out

    async def get_list(self) -> list[SshHostOutSchema]:
        return [self._to_out(row) for row in await self._crud().get_list()]

    async def detail(self, id: int) -> SshHostOutSchema:
        return self._to_out(await self._crud().get_or_404(id=id, msg="SSH 主机不存在"))

    async def create(self, data: SshHostCreateSchema) -> SshHostOutSchema:
        if await self._crud().get(name=data.name):
            raise CustomException(msg="创建失败，主机名称已存在")
        if data.auth_type == "password" and not data.password:
            raise CustomException(msg="密码认证必须提供密码")
        if data.auth_type == "key" and not data.private_key:
            raise CustomException(msg="密钥认证必须提供私钥")
        payload = data.model_dump()
        payload["password"] = CryptoUtil.encrypt(data.password) if data.password else None
        payload["private_key"] = CryptoUtil.encrypt(data.private_key) if data.private_key else None
        payload["passphrase"] = CryptoUtil.encrypt(data.passphrase) if data.passphrase else None
        row = await self._crud().create(data=payload)
        return self._to_out(row)

    async def update(self, id: int, data: SshHostUpdateSchema) -> SshHostOutSchema:
        await self._crud().get_or_404(id=id, msg="SSH 主机不存在")
        exist = await self._crud().get(name=data.name)
        if exist and exist.id != id:
            raise CustomException(msg="更新失败，主机名称已存在")
        payload = data.model_dump(exclude_unset=True)
        for field in ("password", "private_key", "passphrase"):
            value = payload.get(field)
            if value:
                payload[field] = CryptoUtil.encrypt(value)
            else:
                payload.pop(field, None)
        row = await self._crud().update(id=id, data=payload)
        return self._to_out(row)

    async def delete(self, ids: list[int]) -> None:
        await self._crud().delete(ids=ids)

    async def test_connection(self, data: SshHostTestSchema | SshHostModel) -> bool:
        """按给定凭据或已保存主机测试连接（失败抛 CustomException）。"""
        if isinstance(data, SshHostModel):
            password = CryptoUtil.decrypt(data.password)
            private_key = CryptoUtil.decrypt(data.private_key)
            passphrase = CryptoUtil.decrypt(data.passphrase)
            host, port, username, auth_type = data.host, data.port, data.username, data.auth_type
        else:
            password, private_key, passphrase = data.password, data.private_key, data.passphrase
            host, port, username, auth_type = data.host, data.port, data.username, data.auth_type

        def _probe() -> None:
            client = connect_client(
                host=host,
                port=port,
                username=username,
                auth_type=auth_type,
                password=password,
                private_key=private_key,
                passphrase=passphrase,
            )
            client.close()

        try:
            await asyncio.wait_for(asyncio.to_thread(_probe), timeout=_CONNECT_TIMEOUT + 5)
        except TimeoutError as exc:
            raise CustomException(msg="连接超时") from exc
        except CustomException:
            raise
        except Exception as exc:
            reason = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else type(exc).__name__
            raise CustomException(msg=f"连接失败: {reason}") from exc
        return True

    async def test_by_id(self, id: int) -> bool:
        row = await self._crud().get_or_404(id=id, msg="SSH 主机不存在")
        return await self.test_connection(row)

    async def _enabled_host(self, id: int) -> SshHostModel:
        row = await self._crud().get_or_404(id=id, msg="SSH 主机不存在")
        if row.status != 0:
            raise CustomException(msg="该主机已停用")
        return row

    async def open_terminal(self, host_id: int, cols: int, rows: int):
        """打开一个交互终端会话（paramiko invoke_shell）。"""
        row = await self._enabled_host(host_id)
        password = CryptoUtil.decrypt(row.password)
        private_key = CryptoUtil.decrypt(row.private_key)
        passphrase = CryptoUtil.decrypt(row.passphrase)

        def _open() -> tuple[paramiko.SSHClient, paramiko.Channel]:
            client = connect_client(
                host=row.host,
                port=row.port,
                username=row.username,
                auth_type=row.auth_type,
                password=password,
                private_key=private_key,
                passphrase=passphrase,
            )
            channel = client.invoke_shell(width=cols, height=rows)
            return client, channel

        try:
            client, channel = await asyncio.wait_for(asyncio.to_thread(_open), timeout=_CONNECT_TIMEOUT + 5)
        except TimeoutError as exc:
            raise CustomException(msg="终端连接超时") from exc
        except CustomException:
            raise
        except Exception as exc:
            reason = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else type(exc).__name__
            raise CustomException(msg=f"终端连接失败: {reason}") from exc
        return TerminalManager.open(
            user_id=self.auth.user.id or 0,
            host_id=row.id,
            host_name=row.name,
            client=client,
            channel=channel,
            cols=cols,
            rows=rows,
        )

    async def open_log_tail(self, host_id: int, path: str, lines: int):
        """打开日志跟踪会话（在交互 shell 里执行 tail -n N -F）。"""
        session = await self.open_terminal(host_id, cols=160, rows=40)
        logger.info(f"SSH 日志跟踪: user={self.auth.user.username} host={session.host_name} path={path}")
        command = f"tail -n {int(lines)} -F -- {shlex.quote(path)}\r"
        TerminalManager.write(session.session_id, self.auth.user.id or 0, command.encode())
        return session

    async def batch_execute(self, host_ids: list[int], command: str, timeout: int) -> list[BatchExecResultSchema]:
        """在多台主机上执行同一条命令（并发上限 5，单机超时）。"""
        rows = {row.id: row for row in await self._crud().get_list()}
        logger.info(
            f"SSH 批量执行: user={self.auth.user.username} hosts={host_ids} cmd={command[:200]}"
        )
        semaphore = asyncio.Semaphore(_BATCH_CONCURRENCY)

        async def _one(host_id: int) -> BatchExecResultSchema:
            row = rows.get(host_id)
            if row is None:
                return BatchExecResultSchema(
                    host_id=host_id, host_name="", ok=False, exit_status=None,
                    stdout="", stderr="", error="主机不存在", elapsed_ms=0,
                )
            if row.status != 0:
                return BatchExecResultSchema(
                    host_id=host_id, host_name=row.name, ok=False, exit_status=None,
                    stdout="", stderr="", error="主机已停用", elapsed_ms=0,
                )
            async with semaphore:
                started = time.perf_counter()
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self._exec_on_host, row, command, timeout),
                        timeout=timeout + 10,
                    )
                except TimeoutError:
                    return BatchExecResultSchema(
                        host_id=host_id,
                        host_name=row.name,
                        ok=False,
                        exit_status=None,
                        stdout="",
                        stderr="",
                        error=f"执行超时（>{timeout + 10}s）",
                        elapsed_ms=int((time.perf_counter() - started) * 1000),
                    )
                except Exception as exc:  # noqa: BLE001 - 单机失败不影响其它主机
                    reason = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else type(exc).__name__
                    return BatchExecResultSchema(
                        host_id=host_id,
                        host_name=row.name,
                        ok=False,
                        exit_status=None,
                        stdout="",
                        stderr="",
                        error=f"执行失败: {reason}",
                        elapsed_ms=int((time.perf_counter() - started) * 1000),
                    )
                result.elapsed_ms = int((time.perf_counter() - started) * 1000)
                return result

        return list(await asyncio.gather(*(_one(host_id) for host_id in host_ids)))

    def _exec_on_host(self, row: SshHostModel, command: str, timeout: int) -> BatchExecResultSchema:
        """在单台主机执行命令（同步，跑在线程里）。"""
        password = CryptoUtil.decrypt(row.password)
        private_key = CryptoUtil.decrypt(row.private_key)
        passphrase = CryptoUtil.decrypt(row.passphrase)
        client = connect_client(
            host=row.host,
            port=row.port,
            username=row.username,
            auth_type=row.auth_type,
            password=password,
            private_key=private_key,
            passphrase=passphrase,
        )
        try:
            _, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")[:_MAX_CAPTURE]
            err = stderr.read().decode("utf-8", errors="replace")[:_MAX_CAPTURE]
            exit_status = stdout.channel.recv_exit_status()
        finally:
            client.close()
        return BatchExecResultSchema(
            host_id=row.id,
            host_name=row.name,
            ok=exit_status == 0,
            exit_status=exit_status,
            stdout=out,
            stderr=err,
            error="",
            elapsed_ms=0,
        )


class SshSnippetService:
    """命令片段管理"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    def _crud(self) -> SshSnippetCRUD:
        return SshSnippetCRUD(self.auth, self.db)

    async def get_list(self) -> list[SshSnippetOutSchema]:
        return [SshSnippetOutSchema.model_validate(row) for row in await self._crud().get_list()]

    async def create(self, data: SshSnippetCreateSchema) -> SshSnippetOutSchema:
        row = await self._crud().create(data=data.model_dump())
        return SshSnippetOutSchema.model_validate(row)

    async def update(self, id: int, data: SshSnippetUpdateSchema) -> SshSnippetOutSchema:
        await self._crud().get_or_404(id=id, msg="命令片段不存在")
        row = await self._crud().update(id=id, data=data.model_dump())
        return SshSnippetOutSchema.model_validate(row)

    async def delete(self, ids: list[int]) -> None:
        await self._crud().delete(ids=ids)
