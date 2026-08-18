"""SQLAlchemy-модели SAINT CRMP | BOT."""
from datetime import datetime
from typing import Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    vk_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(80))
    global_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_root: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    members: Mapped[list["ConversationMember"]] = relationship(back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    peer_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    custom_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    is_bot_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    members: Mapped[list["ConversationMember"]] = relationship(back_populates="conversation")

class ConversationMember(Base):
    __tablename__ = "conversation_members"
    __table_args__ = (UniqueConstraint("user_id", "conversation_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    local_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    local_nickname: Mapped[str | None] = mapped_column(String(80))
    user: Mapped[User] = relationship(back_populates="members")
    conversation: Mapped[Conversation] = relationship(back_populates="members")

class Level(Base):
    __tablename__ = "levels"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(100))
    is_global: Mapped[bool] = mapped_column(Boolean, default=True)
    commands: Mapped[list[str]] = mapped_column(JSON, default=list)

class Warn(Base):
    __tablename__ = "warns"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    moderator_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="Не указана")
    is_verbal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Ban(Base):
    __tablename__ = "bans"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    moderator_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="Не указана")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Mute(Base):
    __tablename__ = "mutes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    moderator_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="Не указана")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class PointHistory(Base):
    __tablename__ = "points_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    moderator_id: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MonitoringList(Base):
    __tablename__ = "monitoring_lists"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(20))
    samp_nick: Mapped[str] = mapped_column(String(80))

class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
