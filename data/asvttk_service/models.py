import json
from enum import Enum
from typing import Optional, Any

import sqlalchemy
from aiogram.types import Message
from sqlalchemy import JSON, ForeignKey, BigInteger, TypeDecorator, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship

from data.asvttk_service import default
from data.asvttk_service.utils import get_current_time, generate_access_key, generate_session_token


class AccountType(Enum):
    ADMIN = 10
    EMPLOYEE = 9
    STUDENT = 8


class LevelType:
    INFO = "info"
    QUIZ = "quiz"


class FileType:
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"


class MSGS(TypeDecorator):
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps([i.model_dump_json() for i in value])
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            msgs_json = json.loads(value)
            value = [Message.model_validate_json(i) for i in msgs_json]
        return value


Base = declarative_base()


class UserStateOrm(Base):
    __tablename__ = "user_states"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    state: Mapped[Optional[str]] = mapped_column(nullable=True)
    data: Mapped[dict] = mapped_column(JSON)


class KeyOrm(Base):
    __tablename__ = "keys"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    access_key: Mapped[str] = mapped_column(default=generate_access_key, unique=True)
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    is_first_log_in: Mapped[bool] = mapped_column(default=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))


class SessionOrm(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key_id: Mapped[int] = mapped_column(ForeignKey("keys.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(default=generate_session_token, unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_states.user_id", ondelete="CASCADE"))
    date_create: Mapped[int] = mapped_column(default=get_current_time)


class AccountOrm(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[AccountType] = mapped_column(sqlalchemy.Enum(AccountType))
    email: Mapped[Optional[str]] = mapped_column(nullable=True)
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    first_name: Mapped[str]
    last_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    patronymic: Mapped[Optional[str]] = mapped_column(nullable=True)
    training_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trainings.id", ondelete="CASCADE", name="fk_training_id_in_account"), nullable=True)
    date_complete_training: Mapped[Optional[int]] = mapped_column(nullable=True)

    roles = relationship("RoleOrm", secondary="role_and_accounts", back_populates="accounts")
    training = relationship("TrainingOrm", back_populates="students")


class RoleAndAccountOrm(Base):
    __tablename__ = "role_and_accounts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    date_create: Mapped[int] = mapped_column(default=get_current_time)


class RoleOrm(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)
    date_create: Mapped[int] = mapped_column(default=get_current_time)

    accounts = relationship("AccountOrm", secondary="role_and_accounts", back_populates="roles")
    trainings = relationship("TrainingOrm", secondary="training_and_roles", back_populates="roles")


class TrainingAndRoleOrm(Base):
    __tablename__ = "training_and_roles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"))
    date_create: Mapped[int] = mapped_column(default=get_current_time)


class LevelOrm(Base):
    __tablename__ = "levels"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    previous_level_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("levels.id", ondelete="SET NULL"), nullable=True)
    next_level_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("levels.id", ondelete="SET NULL"), nullable=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"))
    type: Mapped[str]
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    title: Mapped[str]
    messages: Mapped[list[Message]] = mapped_column(MSGS)

    training = relationship("TrainingOrm", back_populates="levels")


class LevelAnswerOrm(Base):
    __tablename__ = "level_answers"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id", ondelete="CASCADE"))
    answer_option_ids: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(nullable=True)


class TrainingOrm(Base):
    __tablename__ = "trainings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    message: Mapped[list[Message]] = mapped_column(MSGS, default=[default.DEFAULT_TRAINING_START_MSG])
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    date_start: Mapped[Optional[int]] = mapped_column(nullable=True)
    date_end: Mapped[Optional[int]] = mapped_column(nullable=True)

    students = relationship("AccountOrm", back_populates="training", cascade="all, delete")
    roles = relationship(
        "RoleOrm", secondary="training_and_roles", secondaryjoin="RoleOrm.id == TrainingAndRoleOrm.role_id",
        primaryjoin="TrainingOrm.id == TrainingAndRoleOrm.training_id", back_populates="trainings",
        cascade="all, delete"
    )
    levels = relationship("LevelOrm", back_populates="training", cascade="all, delete")
