"""SSH 运维：主机与命令片段（凭据加密存储）。"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class SshHostModel(ModelMixin, UserMixin):
    """SSH 主机配置（密码/私钥 Fernet 加密；出参不含任何凭据）"""

    __tablename__: str = "ops_ssh_host"
    __table_args__: dict[str, str] = {"comment": "SSH运维主机表"}

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, comment="主机名称")
    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="主机地址")
    port: Mapped[int] = mapped_column(Integer, default=22, nullable=False, comment="SSH端口")
    username: Mapped[str] = mapped_column(String(64), nullable=False, comment="登录用户名")
    auth_type: Mapped[str] = mapped_column(String(16), default="password", nullable=False, comment="认证方式(password/key)")
    password: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="密码(Fernet加密)")
    private_key: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="私钥(Fernet加密)")
    passphrase: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="私钥口令(Fernet加密)")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启用 1:停用)")
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class SshSnippetModel(ModelMixin, UserMixin):
    """常用命令片段"""

    __tablename__: str = "ops_ssh_snippet"
    __table_args__: dict[str, str] = {"comment": "SSH命令片段表"}

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="片段名称")
    command: Mapped[str] = mapped_column(Text, nullable=False, comment="命令内容")
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
