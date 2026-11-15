"""SSH 运维数据契约。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SshHostBaseSchema(BaseModel):
    """主机公共字段（不含凭据）"""

    name: str = Field(..., min_length=1, max_length=64, description="主机名称（唯一）")
    host: str = Field(..., min_length=1, max_length=255, description="主机地址")
    port: int = Field(22, ge=1, le=65535, description="SSH 端口")
    username: str = Field(..., min_length=1, max_length=64, description="登录用户名")
    auth_type: Literal["password", "key"] = Field("password", description="认证方式")
    status: int = Field(0, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(None, max_length=500, description="备注")


class SshHostCreateSchema(SshHostBaseSchema):
    """新建主机（按认证方式提供密码或私钥）"""

    password: str | None = Field(None, max_length=500, description="密码（auth_type=password）")
    private_key: str | None = Field(None, max_length=20000, description="私钥内容（auth_type=key）")
    passphrase: str | None = Field(None, max_length=500, description="私钥口令（可选）")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("主机名称不能为空")
        return value


class SshHostUpdateSchema(SshHostBaseSchema):
    """修改主机（凭据字段不传表示不修改）"""

    password: str | None = Field(None, max_length=500)
    private_key: str | None = Field(None, max_length=20000)
    passphrase: str | None = Field(None, max_length=500)


class SshHostOutSchema(SshHostBaseSchema):
    """主机出参（不含任何凭据）"""

    id: int = Field(..., description="主机ID")
    has_password: bool = Field(False, description="是否已设置密码")
    has_private_key: bool = Field(False, description="是否已设置私钥")

    model_config = ConfigDict(from_attributes=True)


class SshHostTestSchema(BaseModel):
    """按填写中的凭据测试（不落库）"""

    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=64)
    auth_type: Literal["password", "key"] = "password"
    password: str | None = Field(None, max_length=500)
    private_key: str | None = Field(None, max_length=20000)
    passphrase: str | None = Field(None, max_length=500)


class SshSnippetBaseSchema(BaseModel):
    """命令片段公共字段"""

    name: str = Field(..., min_length=1, max_length=64, description="片段名称")
    command: str = Field(..., min_length=1, max_length=4000, description="命令内容")
    description: str | None = Field(None, max_length=500, description="备注")


class SshSnippetCreateSchema(SshSnippetBaseSchema):
    """新建片段"""


class SshSnippetUpdateSchema(SshSnippetBaseSchema):
    """修改片段"""


class SshSnippetOutSchema(SshSnippetBaseSchema):
    """片段出参"""

    id: int = Field(..., description="片段ID")

    model_config = ConfigDict(from_attributes=True)


class TerminalOpenSchema(BaseModel):
    """打开终端会话"""

    host_id: int = Field(..., ge=1, description="SSH 主机ID")
    cols: int = Field(120, ge=20, le=400, description="终端列数")
    rows: int = Field(30, ge=5, le=200, description="终端行数")


class TerminalLogOpenSchema(BaseModel):
    """打开日志跟踪会话（tail -F）"""

    host_id: int = Field(..., ge=1, description="SSH 主机ID")
    path: str = Field(..., min_length=1, max_length=512, description="日志文件路径")
    lines: int = Field(200, ge=1, le=2000, description="初始行数")


class TerminalInputSchema(BaseModel):
    """终端输入（base64 编码的原始字节）"""

    data: str = Field(..., max_length=20000, description="base64 编码的输入内容")


class TerminalResizeSchema(BaseModel):
    """终端尺寸同步"""

    cols: int = Field(..., ge=20, le=400)
    rows: int = Field(..., ge=5, le=200)


class TerminalSessionSchema(BaseModel):
    """终端会话信息"""

    session_id: str = Field(..., description="会话ID")
    host_id: int = Field(..., description="主机ID")
    host_name: str = Field(..., description="主机名称")
    cols: int = Field(..., description="列数")
    rows: int = Field(..., description="行数")
    created_at: str = Field(..., description="创建时间（ISO）")


class TerminalPollSchema(BaseModel):
    """终端轮询结果"""

    data: str = Field("", description="base64 编码的输出（可能为空）")
    closed: bool = Field(False, description="会话/通道是否已关闭")
    exit_status: int | None = Field(None, description="退出码（会话结束时可得）")


class BatchExecSchema(BaseModel):
    """多主机批量执行"""

    host_ids: list[int] = Field(..., min_length=1, max_length=50, description="主机ID列表（最多 50）")
    command: str = Field(..., min_length=1, max_length=2000, description="要执行的命令")
    timeout: int = Field(15, ge=1, le=120, description="每台主机执行超时（秒）")

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("命令不能为空")
        if "\x00" in value:
            raise ValueError("命令不能包含空字节")
        return value


class BatchExecResultSchema(BaseModel):
    """单台主机的批量执行结果"""

    host_id: int = Field(..., description="主机ID")
    host_name: str = Field(..., description="主机名称")
    ok: bool = Field(False, description="是否执行成功")
    exit_status: int | None = Field(None, description="退出码")
    stdout: str = Field("", description="标准输出（截断）")
    stderr: str = Field("", description="标准错误（截断）")
    error: str = Field("", description="连接/执行错误")
    elapsed_ms: int = Field(0, description="耗时（毫秒）")
