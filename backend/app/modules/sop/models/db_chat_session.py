"""
@create_time: 2025/12/19
@Author: GeChao
@File: db_chat_session.py
"""

from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.modules.sop.database import Base


class ChatSession(Base):
    __tablename__ = "db_chat_session"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(128), nullable=False, index=True)
    session_id = Column(String(120), nullable=False, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)
    create_user = Column(String(128), nullable=False, default="system")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    update_user = Column(String(128), nullable=False, default="system")

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
