from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import SshHostModel, SshSnippetModel
from .schema import SshHostCreateSchema, SshHostUpdateSchema, SshSnippetCreateSchema, SshSnippetUpdateSchema


class SshHostCRUD(CRUDBase[SshHostModel, SshHostCreateSchema, SshHostUpdateSchema]):
    """SSH 主机数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SshHostModel, auth=auth, db=db)


class SshSnippetCRUD(CRUDBase[SshSnippetModel, SshSnippetCreateSchema, SshSnippetUpdateSchema]):
    """命令片段数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SshSnippetModel, auth=auth, db=db)
