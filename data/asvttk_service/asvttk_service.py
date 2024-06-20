import itertools
from typing import Any, Optional

from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from typeguard import typechecked

from data.asvttk_service import types
from data.asvttk_service.database import database
from data.asvttk_service.exceptions import ObjectNotFoundError, TokenNotValidError, \
    KeyNotFoundError, AccountNotFoundError, AccessError, RoleNotUniqueNameError, NotFoundError, TrainingStateError, \
    TrainingIsActiveError, TrainingIsNotActiveError, LevelAnswerAlreadyExistsError, TrainingHasStudentsError
from data.asvttk_service.mappers import account_orm_to_account_data, role_orm_to_role_data, \
    training_orm_to_training_data, account_orm_to_employee_data, account_orm_to_student_data, level_orm_to_level_data, \
    level_answer_orm_to_level_answer_data
from data.asvttk_service.models import KeyOrm, SessionOrm, AccountOrm, AccountType, RoleOrm, TrainingOrm, \
    TrainingAndRoleOrm, RoleAndAccountOrm, LevelOrm, LevelAnswerOrm, LevelType
from data.asvttk_service.types import AccountData, RoleData, EmployeeData, CreatedAccountData, TrainingData, LevelData, \
    StudentData, LevelAnswerData, StudentProgressData, StudentProgressState
from data.asvttk_service.utils import generate_session_token, generate_access_key, email_check, initials_check, \
    empty_check, get_current_time
from src import strings


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


async def __check_has_training(s: AsyncSession, training_id: int, employee_id: int):
    query = await s.execute(select(RoleOrm).options(joinedload(RoleOrm.trainings))
                            .join(RoleAndAccountOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                            .filter(RoleAndAccountOrm.account_id == employee_id))
    roles = query.scalars().unique().all()
    training_ids = list(itertools.chain(*[[n.id for n in i.trainings] for i in roles]))
    if training_id not in training_ids:
        raise AccessError()


async def __check_training(s: AsyncSession, training_id: int, student_id: int):
    query = await s.execute(select(AccountOrm).filter(AccountOrm.type == AccountType.STUDENT,
                                                      AccountOrm.id == student_id))
    student = query.scalars().first()
    if student.training_id != training_id:
        raise AccessError()


async def __check_training_has_not_students(s: AsyncSession, training_id: int):
    query = await s.execute(select(AccountOrm).filter(AccountOrm.type == AccountType.STUDENT,
                                                      AccountOrm.training_id == training_id))
    students = query.scalars().all()
    if students:
        raise TrainingHasStudentsError()


@typechecked()
async def check_training_has_not_students(token: str, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE, AccountType.STUDENT]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        if token_data.account.type == AccountType.STUDENT:
            await __check_training(s, training_id, token_data.account.id)
        await __check_training_has_not_students(s, training_id)


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
async def check_access_key(access_key: str):
    async with database.session_factory() as s:
        query = await s.execute(select(KeyOrm).filter(KeyOrm.access_key == access_key))
        key = query.scalars().first()
        if not key:
            raise KeyNotFoundError


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
        if is_first:
            key_orm.access_key = generate_access_key()
            key_orm.is_first_log_in = False
        token = generate_session_token()
        new_session_orm = SessionOrm(key_id=key_orm.id, token=token, user_id=user_id)
        s.add(new_session_orm)
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
        query = await s.execute(
            select(AccountOrm).options(joinedload(AccountOrm.roles))
            .filter(AccountOrm.type == AccountType.EMPLOYEE)
            .order_by(AccountOrm.date_create)
        )
        employees = query.unique().scalars().all()
        employees_data = [
            account_orm_to_employee_data(i, [role_orm_to_role_data(r) for r in i.roles]) for i in employees]
        return employees_data


@typechecked
async def get_employee_by_id(token: str, employee_id: int) -> EmployeeData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError
        if token_data.account.type == AccountType.EMPLOYEE and token_data.account.id != employee_id:
            raise AccessError
        query = await s.execute(select(AccountOrm).options(joinedload(AccountOrm.roles))
                                .filter(AccountOrm.type == AccountType.EMPLOYEE, AccountOrm.id == employee_id))
        employee = query.scalars().first()
        if not employee:
            raise NotFoundError()
        return account_orm_to_employee_data(employee, [role_orm_to_role_data(r) for r in employee.roles])


@typechecked
async def __create_account(s: AsyncSession, account_type: AccountType, first_name: str,
                           last_name: Optional[str] = None, patronymic: Optional[str] = None,
                           email: Optional[str] = None, training_id: Optional[int] = None) -> CreatedAccountData:
    email_check(email)
    initials_check(first_name, last_name, patronymic)
    employees_orm = AccountOrm(type=account_type, email=email, first_name=first_name, last_name=last_name,
                               patronymic=patronymic, training_id=training_id)
    s.add(employees_orm)
    await s.flush()
    key_orm = KeyOrm(account_id=employees_orm.id)
    s.add(key_orm)
    await s.flush()
    return CreatedAccountData(employees_orm.id, key_orm.access_key)


@typechecked
async def get_account_by_token(token: str) -> AccountData | EmployeeData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type == AccountType.ADMIN:
            return await get_account_by_id(token, token_data.account.id)
        elif token_data.account.type == AccountType.EMPLOYEE:
            return await get_employee_by_id(token, token_data.account.id)
        elif token_data.account.type == AccountType.STUDENT:
            return await get_student_by_id(token, token_data.account.id)
        else:
            raise ValueError()


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


@typechecked
async def delete_employee(token: str, employee_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(AccountOrm).filter(AccountOrm.id == employee_id))
        account_orm = query.scalars().first()
        if not account_orm:
            raise NotFoundError
        await s.delete(account_orm)
        await s.commit()


@typechecked
async def update_email_employee(token: str, employee_id: int, email: Optional[str] = None):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(AccountOrm).filter(AccountOrm.id == employee_id))
        account_orm = query.scalars().first()
        if not account_orm:
            raise NotFoundError
        if email == '-':
            email = None
        email_check(email)
        account_orm.email = email
        await s.commit()


@typechecked
async def update_full_name_employee(token: str, employee_id: int, first_name: Optional[str] = None,
                                    last_name: Optional[str] = None, patronymic: Optional[str] = None):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(AccountOrm).filter(AccountOrm.id == employee_id))
        account_orm = query.scalars().first()
        if not account_orm:
            raise NotFoundError
        first_name, last_name, patronymic = (None if i == '-' else i for i in (first_name, last_name, patronymic))
        initials_check(first_name, last_name, patronymic)
        account_orm.first_name = first_name
        account_orm.last_name = last_name
        account_orm.patronymic = patronymic
        await s.commit()


@typechecked
async def add_role_to_employee(token: str, employee_id: int, role_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(AccountOrm).filter(AccountOrm.id == employee_id))
        employee = query.scalars().first()
        query = await s.execute(select(RoleOrm).filter(RoleOrm.id == role_id))
        role = query.scalars().first()
        if employee.type != AccountType.EMPLOYEE:
            raise ValueError("Only for employees")
        if not employee or not role:
            raise NotFoundError()
        account_and_role = RoleAndAccountOrm(account_id=employee_id, role_id=role_id)
        s.add(account_and_role)
        await s.commit()


@typechecked
async def remove_role_from_employee(token: str, employee_id: int, role_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(RoleAndAccountOrm)
                                .filter(RoleAndAccountOrm.role_id == role_id)
                                .filter(RoleAndAccountOrm.account_id == employee_id))
        account_and_role = query.scalars().first()
        if not account_and_role:
            raise NotFoundError()
        await s.delete(account_and_role)
        await s.commit()


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
async def get_all_roles(token: str, account_id: Optional[int] = None) -> list[RoleData]:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError
        if token_data.account.type == AccountType.EMPLOYEE and not account_id:
            account_id = token_data.account.id
        if account_id:
            query = await s.execute(select(AccountOrm).options(joinedload(AccountOrm.roles))
                                    .filter(AccountOrm.id == account_id).order_by(RoleOrm.date_create))
            account = query.scalars().first()
            if not account:
                raise NotFoundError
            if account.type != AccountType.EMPLOYEE:
                raise ValueError("Only for employees")
            roles = [role_orm_to_role_data(i) for i in account.roles]
        else:
            query = await s.execute(select(RoleOrm).order_by(RoleOrm.date_create).order_by(RoleOrm.date_create))
            roles = [role_orm_to_role_data(i) for i in query.scalars().all()]
        return roles


@typechecked
async def get_role_by_id(token: str, role_id: int) -> RoleData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError
        query = await s.execute(select(RoleOrm).filter(RoleOrm.id == role_id))
        role_orm = query.scalars().first()
        if not role_orm:
            raise NotFoundError
        if token_data.account.type == AccountType.EMPLOYEE:
            query = await s.execute(select(AccountOrm).options(joinedload(AccountOrm.roles))
                                    .filter(AccountOrm.id == token_data.account.id))
            allowed_role_ids = [i.id for i in query.scalars().unique().first().roles]
            if role_id not in allowed_role_ids:
                raise AccessError()
        query = await s.execute(select(RoleOrm).options(joinedload(RoleOrm.accounts))
                                .options(joinedload(RoleOrm.trainings)).filter(RoleOrm.id == role_id))
        role = query.scalars().unique().first()
        trainings = [training_orm_to_training_data(i, None, None) for i in role.trainings]
        accounts = [account_orm_to_account_data(i) for i in role.accounts]
        role = role_orm_to_role_data(role_orm, trainings, accounts)
        return role


@typechecked
async def add_training_to_role(token: str, role_id: int, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(TrainingOrm).filter(TrainingOrm.id == training_id))
        training = query.scalars().first()
        query = await s.execute(select(RoleOrm).filter(RoleOrm.id == role_id))
        role = query.scalars().first()
        if not training or not role:
            raise NotFoundError()
        training_and_role = TrainingAndRoleOrm(training_id=training_id, role_id=role_id)
        s.add(training_and_role)
        await s.commit()


@typechecked
async def remove_training_from_role(token: str, role_id: int, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type != AccountType.ADMIN:
            raise AccessError()
        query = await s.execute(select(TrainingAndRoleOrm)
                                .filter(TrainingAndRoleOrm.role_id == role_id)
                                .filter(TrainingAndRoleOrm.training_id == training_id))
        training_and_role = query.scalars().first()
        if not training_and_role:
            raise NotFoundError()
        await s.delete(training_and_role)
        await s.commit()


# Trainings
@typechecked
async def create_training(token: str, name: str, start_text: Optional[str] = None,
                          html_start_text: Optional[str] = None, role_id: Optional[int] = None) -> TrainingData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            query = await s.execute(select(AccountOrm).options(joinedload(AccountOrm.roles))
                                    .filter(AccountOrm.id == token_data.account.id))
            allowed_role_ids = [i.id for i in query.scalars().first().roles]
            if role_id is None and len(allowed_role_ids) == 1:
                role_id = allowed_role_ids[0]
            if role_id is None:
                raise ValueError("The employee must enter the role_id")
            if role_id not in allowed_role_ids:
                raise AccessError("The employee does not have this role")
        empty_check(name)
        new_training = TrainingOrm(name=name)
        if bool(start_text) != bool(html_start_text):
            raise ValueError("The start_text has a value, but html_start_text does not, or vice versa")
        elif start_text and html_start_text:
            new_training.start_text = start_text
            new_training.html_start_text = html_start_text
        else:
            new_training.start_text = strings.LEVEL__START_TEXT_DEFAULT
            new_training.html_start_text = strings.LEVEL__START_TEXT_DEFAULT
        s.add(new_training)
        await s.flush()
        training_data = training_orm_to_training_data(new_training, None, None)
        if role_id:
            training_and_role = TrainingAndRoleOrm(role_id=role_id, training_id=new_training.id)
            s.add(training_and_role)
        await s.commit()
        return training_data


@typechecked
async def get_all_trainings(token: str):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            query = await s.execute(select(RoleOrm)
                                    .join(RoleAndAccountOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                                    .filter(RoleAndAccountOrm.account_id == token_data.account.id))
            roles = query.scalars().all()
            if not roles:
                raise AccessError()
            query = await s.execute(select(TrainingOrm)
                                    .options(joinedload(TrainingOrm.students))
                                    .join(TrainingAndRoleOrm, TrainingOrm.id == TrainingAndRoleOrm.training_id)
                                    .join(RoleOrm, TrainingAndRoleOrm.role_id == RoleOrm.id)
                                    .join(RoleAndAccountOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                                    .filter(RoleAndAccountOrm.account_id == token_data.account.id)
                                    .order_by(TrainingOrm.date_create))
        else:
            query = await s.execute(select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                    .order_by(TrainingOrm.date_create))
        trainings = query.scalars().unique().all()
        trainings_data = []
        for i in trainings:
            students = [account_orm_to_student_data(n, None, None) for n in i.students]
            trainings_data.append(training_orm_to_training_data(i, students, None))
        return trainings_data


@typechecked
async def get_training_by_id(token: str, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        query = await s.execute(select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                .options(joinedload(TrainingOrm.levels)).filter(TrainingOrm.id == training_id))
        training = query.scalars().first()
        if not training:
            raise NotFoundError()
        students = [account_orm_to_student_data(i, None, None) for i in training.students]
        levels = [level_orm_to_level_data(i, None, None, None) for i in training.levels]
        return training_orm_to_training_data(training, students, levels)


def __training_is_started(training: TrainingOrm) -> bool:
    return training.date_start and not training.date_end


async def __training_is_started_check(s: AsyncSession, training_id: int):
    query = await s.execute(select(TrainingOrm).filter(TrainingOrm.id == training_id))
    training = query.scalars().first()
    if __training_is_started(training):
        raise TrainingIsActiveError()


async def training_is_started_check(token: str, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE, AccountType.STUDENT]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        if token_data.account.type == AccountType.STUDENT:
            await __check_training(s, training_id, token_data.account.id)
        await __training_is_started_check(s, training_id)


async def __training_is_not_started_check(s: AsyncSession, training_id: int):
    query = await s.execute(select(TrainingOrm).filter(TrainingOrm.id == training_id))
    training = query.scalars().first()
    if not __training_is_started(training):
        raise TrainingIsNotActiveError()


async def training_is_not_started_check(token: str, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE, AccountType.STUDENT]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        if token_data.account.type == AccountType.STUDENT:
            await __check_training(s, training_id, token_data.account.id)
        await __training_is_not_started_check(s, training_id)


@typechecked
async def update_start_msg_training(token: str, training_id: int, msg: list[Message]):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        query = await s.execute(select(TrainingOrm).filter(TrainingOrm.id == training_id))
        training = query.scalars().first()
        if not training:
            return NotFoundError()
        await __training_is_started_check(s, training_id)
        await __check_training_has_not_students(s, training_id)
        training.message = msg
        await s.commit()


@typechecked
async def delete_training(token: str, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        query = await s.execute(select(TrainingOrm).filter(TrainingOrm.id == training_id))
        training = query.scalars().first()
        if not training:
            return NotFoundError()
        await __training_is_started_check(s, training_id)
        await __check_training_has_not_students(s, training_id)
        await s.delete(training)
        await s.commit()


@typechecked
async def update_name_training(token: str, training_id: int, name: Optional[str] = None):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        query = await s.execute(select(TrainingOrm).filter(TrainingOrm.id == training_id))
        training = query.scalars().first()
        if not training:
            raise NotFoundError
        await __training_is_started_check(s, training_id)
        await __check_training_has_not_students(s, training_id)
        training.name = name
        await s.commit()


@typechecked
async def start_training(token: str, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        query = await s.execute(select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                .filter(TrainingOrm.id == training_id))
        training = query.scalars().unique().first()
        if not training:
            raise NotFoundError
        if training.date_start and not training.date_end:
            raise TrainingStateError()
        training.date_start = get_current_time()
        training.date_end = None
        for student in training.students:
            await s.delete(student)
        await s.commit()


@typechecked
async def stop_training(token: str, training_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        query = await s.execute(select(TrainingOrm).filter(TrainingOrm.id == training_id))
        training = query.scalars().first()
        if not training:
            raise NotFoundError
        if not (training.date_start and not training.date_end):
            raise TrainingStateError()
        training.date_end = get_current_time()
        await s.commit()


# Levels
@typechecked
async def create_level(token: str, level_type: str, training_id: int, title: str, messages: list[Message]):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        await __training_is_started_check(s, training_id)
        await __check_training_has_not_students(s, training_id)
        query = await s.execute(select(LevelOrm).filter(LevelOrm.training_id == training_id,
                                                        LevelOrm.next_level_id == None))
        last_level = query.scalars().first()
        last_level_id = last_level.id if last_level else None
        level = LevelOrm(previous_level_id=last_level_id, training_id=training_id, type=level_type,
                         title=title, messages=messages)
        s.add(level)
        await s.flush()
        if last_level:
            last_level.next_level_id = level.id
        await s.commit()


@typechecked
async def update_content_level_by_id(token: str, level_type: str, level_id: int, messages: list[Message]):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        query = await s.execute(select(LevelOrm).filter(LevelOrm.id == level_id))
        level = query.scalars().first()
        if not level:
            raise NotFoundError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, level.training_id, token_data.account.id)
        await __training_is_started_check(s, level.training_id)
        await __check_training_has_not_students(s, level.training_id)
        level.messages = messages
        level.type = level_type
        await s.commit()


@typechecked
async def update_title_level_by_id(token: str, level_id: int, title: str):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        query = await s.execute(select(LevelOrm).filter(LevelOrm.id == level_id))
        level = query.scalars().first()
        if not level:
            raise NotFoundError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, level.training_id, token_data.account.id)
        await __training_is_started_check(s, level.training_id)
        await __check_training_has_not_students(s, level.training_id)
        level.title = title
        await s.commit()


@typechecked
async def delete_level_by_id(token: str, level_id: int):
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        query = await s.execute(select(LevelOrm).filter(LevelOrm.id == level_id))
        level = query.scalars().first()
        if not level:
            raise NotFoundError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, level.training_id, token_data.account.id)
        await __training_is_started_check(s, level.training_id)
        await __check_training_has_not_students(s, level.training_id)
        if level.next_level_id:
            query = await s.execute(select(LevelOrm).filter(LevelOrm.id == level.next_level_id))
            next_level = query.scalars().first()
            next_level.previous_level_id = level.previous_level_id
        if level.previous_level_id:
            query = await s.execute(select(LevelOrm).filter(LevelOrm.id == level.previous_level_id))
            previous_level = query.scalars().first()
            previous_level.next_level_id = level.next_level_id
        await s.delete(level)
        await s.commit()


async def __get_levels_sorted(s: AsyncSession, training_id: int):
    query = await s.execute(select(LevelOrm).options(joinedload(LevelOrm.training))
                            .filter(LevelOrm.training_id == training_id))
    levels = query.scalars().unique().all()
    first_level = next((lvl for lvl in levels if lvl.previous_level_id is None), None)
    if first_level is None:
        return []
    levels_sorted = []
    current_level = first_level
    while current_level is not None:
        levels_sorted.append(current_level)
        current_level = next((lvl for lvl in levels if lvl.id == current_level.next_level_id), None)
    return levels_sorted


@typechecked
async def get_levels_by_training(token: str, training_id: int) -> list[LevelData]:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        levels = await __get_levels_sorted(s, training_id)
        levels_data = []
        for i in levels:
            training_data = training_orm_to_training_data(i.training, None, None)
            levels_data.append(level_orm_to_level_data(i, levels.index(i) + 1, training_data, None))
        return levels_data


@typechecked
async def get_level_by_id(token: str, level_id: int) -> LevelData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        query = await s.execute(select(LevelOrm).options(joinedload(LevelOrm.training))
                                .options(joinedload(LevelOrm.answers))
                                .filter(LevelOrm.id == level_id))
        level = query.scalars().unique().first()
        if not level:
            raise NotFoundError()
        levels = await __get_levels_sorted(s, level.training_id)
        index = next((i for i in range(len(levels)) if levels[i].id == level_id), None)
        if index is None:
            raise ValueError
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, level.training_id, token_data.account.id)
        training_data = training_orm_to_training_data(level.training, None, None)
        answers = [level_answer_orm_to_level_answer_data(i, None, None) for i in level.answers]
        return level_orm_to_level_data(level, index + 1, training_data, answers=answers)


# Students
@typechecked
async def create_student(token: str, training_id: int, first_name: str, last_name: Optional[str] = None,
                         patronymic: Optional[str] = None) -> CreatedAccountData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
            raise AccessError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, training_id, token_data.account.id)
        await __training_is_not_started_check(s, training_id)
        res = await __create_account(s, AccountType.STUDENT, first_name, last_name, patronymic, training_id=training_id)
        await s.commit()
        return res


@typechecked
async def get_student_by_id(token: str, student_id: int) -> StudentData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE, AccountType.STUDENT]:
            raise AccessError
        if token_data.account.type == AccountType.STUDENT and token_data.account.id != student_id:
            raise AccessError
        query = await s.execute(select(AccountOrm).options(joinedload(AccountOrm.training))
                                .options(joinedload(AccountOrm.answers))
                                .filter(AccountOrm.type == AccountType.STUDENT, AccountOrm.id == student_id))
        student = query.scalars().first()
        if not student:
            raise NotFoundError()
        training = training_orm_to_training_data(student.training, None, None)
        answers = [level_answer_orm_to_level_answer_data(i, None, None) for i in student.answers]
        return account_orm_to_student_data(student, training=training, answers=answers)


@typechecked
async def get_student_progress(token: str, student_id: Optional[int] = None) -> StudentProgressData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE, AccountType.STUDENT]:
            raise AccessError()
        if token_data.account.type == AccountType.STUDENT and (not student_id):
            student_id = token_data.account.id
        if token_data.account.type == AccountType.STUDENT and student_id != token_data.account.id:
            raise AccessError()
        query = await s.execute(select(AccountOrm)
                                .options(joinedload(AccountOrm.training))
                                .options(joinedload(AccountOrm.answers).joinedload(LevelAnswerOrm.level))
                                .filter(AccountOrm.type == AccountType.STUDENT, AccountOrm.id == student_id))
        student = query.scalars().first()
        if not student:
            raise NotFoundError()
        if token_data.account.type == AccountType.EMPLOYEE:
            await __check_has_training(s, student.training_id, token_data.account.id)
        is_access = __training_is_started(student.training)
        all_levels = await __get_levels_sorted(s, student.training_id)
        level_ids_by_answers = [i.level_id for i in student.answers]
        not_completed_levels = [i for i in all_levels if i.id not in level_ids_by_answers]
        progress_state = StudentProgressState.COMPLETED
        current_level = None
        if len(not_completed_levels) == len(all_levels):
            progress_state = StudentProgressState.START
            current_level = not_completed_levels[0]
        elif not_completed_levels:
            progress_state = StudentProgressState.LEVEL
            current_level = not_completed_levels[0]
        answers_data = [level_answer_orm_to_level_answer_data(i, None, None) for i in student.answers]
        student_data = account_orm_to_student_data(student, None, None)
        if current_level:
            current_level_data = level_orm_to_level_data(current_level, None, None, None)
        else:
            current_level_data = None
        all_level = [level_orm_to_level_data(i, None, None, None) for i in all_levels]
        training_data = training_orm_to_training_data(student.training, None, all_level)
        res = StudentProgressData(is_access=is_access, student=student_data, progress_state=progress_state,
                                  current_level=current_level_data, answers=answers_data, training=training_data)
        return res


# LevelAnswer
@typechecked
async def create_level_answer(token: str, level_id: int,
                              answer_option_ids: Optional[list[int]] = None) -> LevelAnswerData:
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        if token_data.account.type not in [AccountType.STUDENT]:
            raise AccessError
        query = await s.execute(select(LevelOrm).filter(LevelOrm.id == level_id))
        level = query.scalars().first()
        if not level:
            raise NotFoundError()
        await __check_training(s, level.training_id, token_data.account.id)
        await __training_is_not_started_check(s, level.training_id)
        query = await s.execute(select(LevelAnswerOrm).filter(LevelAnswerOrm.level_id == level_id,
                                                              LevelAnswerOrm.account_id == token_data.account.id))
        exist_level_answer = query.scalars().first()
        if exist_level_answer:
            raise LevelAnswerAlreadyExistsError()

        if level.type == LevelType.QUIZ and answer_option_ids:
            msg: Message = level.messages[0]
            is_correct = msg.poll.correct_option_id == answer_option_ids[0]
            level_answer = LevelAnswerOrm(account_id=token_data.account.id, level_id=level_id, is_correct=is_correct,
                                          answer_option_ids=answer_option_ids)
        elif level.type == LevelType.INFO:
            level_answer = LevelAnswerOrm(account_id=token_data.account.id, level_id=level_id)
        else:
            raise ValueError()

        s.add(level_answer)
        await s.flush()
        level_data = level_orm_to_level_data(level, None, None, None)
        student = account_orm_to_student_data(token_data.account, None, None)
        res = level_answer_orm_to_level_answer_data(level_answer, level_data, student)
        await s.commit()
        return res
