from typing import Any, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typeguard import typechecked

from data.asvttk_service import types
from data.asvttk_service.database import database
from data.asvttk_service.exceptions import ObjectNotFoundError, KeyHasSessionError, TokenNotValidError, \
    KeyNotFoundError, AccountNotFoundError, AccessError
from data.asvttk_service.mappers import account_orm_to_account_data
from data.asvttk_service.models import KeyOrm, SessionOrm, AccountOrm
from data.asvttk_service.types import AccountData
from data.asvttk_service.utils import generate_session_token, generate_access_key


class ValidateByTokenData:
    def __init__(self, account: AccountOrm, session: SessionOrm, key: KeyOrm):
        self.account = account
        self.session = session
        self.key = key


async def __get_first_where(s: AsyncSession, table: Any, where: Any, null_safe: bool = True,
                            exception: Optional[Exception] = None) -> Any:
    query = await s.execute(select(table).filter(where))
    obj = query.scalars().first()
    if not obj and null_safe:
        if not exception:
            exception = ObjectNotFoundError(table.__tablename__)
        raise exception
    return obj


async def __validate_by_token(s: AsyncSession, token: str) -> ValidateByTokenData:
    query = await s.execute(select(SessionOrm).filter(SessionOrm.token == token))
    session = query.scalars().first()
    if not session:
        raise TokenNotValidError
    key: KeyOrm = await __get_first_where(s, KeyOrm, KeyOrm.id == session.key_id)
    account: AccountOrm = await __get_first_where(s, AccountOrm, AccountOrm.id == key.account_id)
    return ValidateByTokenData(session=session, key=key, account=account)


@typechecked
async def log_out(token: str):
    async with database.session_factory() as s:
        token_session_orm = await __validate_by_token(s, token)
        await s.delete(token_session_orm.session)
        await s.commit()


@typechecked
async def log_in(user_id: int, key: str) -> types.LogInData:
    async with database.session_factory() as s:
        key_orm = await __get_first_where(s, KeyOrm, KeyOrm.access_key == key, exception=KeyNotFoundError())
        current_session: Optional[SessionOrm] = await __get_first_where(s, SessionOrm, SessionOrm.user_id == user_id,
                                                                        null_safe=False)
        if current_session:
            try:
                await log_out(current_session.token)
            except TokenNotValidError as _:
                pass
        is_first = key_orm.is_first_log_in
        token = generate_session_token(user_id)
        new_session_orm = SessionOrm(key_id=key_orm.id, token=token, user_id=user_id)
        s.add(new_session_orm)
        if is_first:
            key_orm.access_key = generate_access_key()
            key_orm.is_first_log_in = False
        access_key = key_orm.access_key
        account_id = key_orm.account_id
        account_orm: AccountOrm = await __get_first_where(s, AccountOrm, AccountOrm.id == account_id)
        account_type = account_orm.type
        await s.commit()
        return types.LogInData(token=token, is_first=is_first, access_key=access_key, account_id=account_id,
                               account_type=account_type)


@typechecked
async def get_account_by_id(token: str, account_id: Optional[int] = None) -> AccountData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        account_orm = token_data.account
        if account_id and account_orm.id != account_id:
            account_orm = await __get_first_where(s, AccountOrm, AccountOrm.id == account_id,
                                                  exception=AccountNotFoundError())
        if token_data.account.type.value < account_orm.type.value:
            raise AccessError()
        return account_orm_to_account_data(account_orm)



