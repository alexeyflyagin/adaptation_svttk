from enum import Enum
from typing import Optional

import sqlalchemy
from sqlalchemy import JSON, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship

from data.asvttk_service.utils import get_current_time, generate_access_key, generate_session_token


class AccountType(Enum):
    ADMIN = 10
    EMPLOYEE = 9
    STUDENT = 8


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


class TrainingAndRoleOrm(Base):
    __tablename__ = "training_and_roles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"))


class TrainingOrm(Base):
    __tablename__ = "trainings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    start_text: Mapped[str]
    html_start_text: Mapped[str]
    photo_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    date_start: Mapped[Optional[int]] = mapped_column(nullable=True)
    date_end: Mapped[Optional[int]] = mapped_column(nullable=True)


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
    text: Mapped[Optional[str]] = mapped_column(nullable=True)
    html_text: Mapped[Optional[str]] = mapped_column(nullable=True)
    photo_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    video_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    document_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    options: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    correct_option_ids: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    quiz_comment: Mapped[Optional[str]] = mapped_column(nullable=True)


class LevelAnswerOrm(Base):
    __tablename__ = "level_answers"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date_create: Mapped[int] = mapped_column(default=get_current_time)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id", ondelete="CASCADE"))
    answer_option_ids: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(nullable=True)