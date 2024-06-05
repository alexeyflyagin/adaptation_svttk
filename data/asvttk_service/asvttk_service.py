from typing import Any, Optional, Type

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typeguard import typechecked

from data.asvttk_service import types
from data.asvttk_service.database import database
from data.asvttk_service.exceptions import ObjectNotFoundError, TokenNotValidError, \
    KeyNotFoundError, AccountNotFoundError, AccessError, RoleNotUniqueNameError, NotFoundError, EmailValueError
from data.asvttk_service.mappers import account_orm_to_account_data, role_orm_to_role_data, \
    training_orm_to_training_data, account_orm_to_employee_data
from data.asvttk_service.models import KeyOrm, SessionOrm, AccountOrm, AccountType, RoleOrm, TrainingOrm, \
    TrainingAndRoleOrm, RoleAndAccountOrm
from data.asvttk_service.types import AccountData, RoleData, EmployeeData, CreatedAccountData
from data.asvttk_service.utils import generate_session_token, generate_access_key, email_check, initials_check


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
async def token_validate(token: Optional[str]):
    if not token:
        raise TokenNotValidError()
    async with database.session_factory() as s:
        await __validate_by_token(s, token)


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
        token = generate_session_token()
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


@typechecked
async def get_all_employees(token: str) -> list[EmployeeData]:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError
        query = await s.execute(select(AccountOrm).filter(AccountOrm.type == AccountType.EMPLOYEE))
        employees = query.scalars().all()
        employees_data = [account_orm_to_employee_data(i, []) for i in employees]
        return employees_data


@typechecked
async def __create_account(s: AsyncSession, account_type: AccountType, first_name: str,
                           last_name: Optional[str] = None, patronymic: Optional[str] = None,
                           email: Optional[str] = None, training: Optional[int] = None) -> CreatedAccountData:
    email_check(email)
    initials_check(first_name, last_name, patronymic)
    employees_orm = AccountOrm(type=AccountType.EMPLOYEE, email=email, first_name=first_name, last_name=last_name,
                               patronymic=patronymic)
    s.add(employees_orm)
    await s.flush()
    key_orm = KeyOrm(account_id=employees_orm.id)
    s.add(key_orm)
    await s.flush()
    return CreatedAccountData(employees_orm.id, key_orm.access_key)


@typechecked
async def create_employee(token: str, first_name: str, last_name: Optional[str] = None,
                          patronymic: Optional[str] = None, email: Optional[str] = None) -> CreatedAccountData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        res = await __create_account(s, AccountType.EMPLOYEE, first_name, last_name, patronymic, email)
        await s.commit()
        return res


# Roles
@typechecked
async def create_role(token: str, name: str) -> RoleData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        if len(name) > 15:
            raise ValueError()
        new_role = RoleOrm(name=name)
        try:
            s.add(new_role)
            await s.flush()
            res = role_orm_to_role_data(new_role)
            await s.commit()
        except IntegrityError:
            raise RoleNotUniqueNameError()
        return res


@typechecked
async def delete_role(token: str, role_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(RoleOrm).filter(RoleOrm.id == role_id))
        role_orm = query.scalars().first()
        if not role_orm:
            raise NotFoundError
        await s.delete(role_orm)
        await s.commit()


@typechecked
async def update_role(token: str, role_id: int, name: str):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(RoleOrm).filter(RoleOrm.id == role_id))
        role_orm = query.scalars().first()
        if not role_orm:
            raise NotFoundError
        if len(name) > 15:
            raise ValueError()
        role_orm.name = name
        try:
            await s.commit()
        except IntegrityError:
            raise RoleNotUniqueNameError()


@typechecked
async def get_all_roles(token: str) -> list[RoleData]:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError
        query = await s.execute(select(RoleOrm))
        roles = [role_orm_to_role_data(i) for i in query.scalars().all()]
        return roles


@typechecked
async def get_role_by_id(token: str, role_id: int) -> RoleData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError
        query = await s.execute(select(RoleOrm).filter(RoleOrm.id == role_id))
        role_orm = query.scalars().first()
        if not role_orm:
            raise NotFoundError
        query = await s.execute(select(TrainingOrm)
                                .join(TrainingAndRoleOrm, TrainingOrm.id == TrainingAndRoleOrm.training_id)
                                .join(RoleOrm, RoleOrm.id == TrainingAndRoleOrm.role_id)
                                .filter(RoleOrm.id == role_id))
        trainings = [training_orm_to_training_data(i) for i in query.scalars().all()]
        query = await s.execute(select(AccountOrm)
                                .join(RoleAndAccountOrm, RoleAndAccountOrm.account_id == AccountOrm.id)
                                .join(RoleOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                                .filter(RoleOrm.id == role_id))
        accounts = [account_orm_to_account_data(i) for i in query.scalars().all()]
        role = role_orm_to_role_data(role_orm, trainings, accounts)
        return role
