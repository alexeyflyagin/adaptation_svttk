import itertools
import logging
import uuid
from typing import Any

from sqlalchemy import select, CursorResult, Result
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from typeguard import typechecked

from data.asvttk_service.database import database
from data.asvttk_service.datetime_utils import get_date_str, DateFormat
from data.asvttk_service.exceptions import *
from data.asvttk_service.mappers import *
from data.asvttk_service.models import *
from data.asvttk_service.types import *
from data.asvttk_service.utils import *
from data.asvttk_service.xlsx_generation import xlsx_engine
from data.asvttk_service.xlsx_generation.tables import RTrainingState, RStudentState, ReportRT

logger = logging.getLogger(__name__)


class ValidateByTokenData:
    def __init__(self, account: AccountOrm, session: SessionOrm, key: KeyOrm):
        self.account = account
        self.session = session
        self.key = key


async def __safe_execute(s: AsyncSession, query: Any,
                         e: Optional[Exception] = NotFoundError()) -> Result | CursorResult:
    res = await s.execute(query)
    res_items = res.unique().fetchall()
    if not len(res_items) and e:
        raise e
    res = await s.execute(query)
    return res


async def __validate_by_token(s: AsyncSession, token: Optional[str]) -> ValidateByTokenData:
    if token is None:
        raise TokenNotValidError()
    query = await __safe_execute(s, select(SessionOrm).filter(SessionOrm.token == token).with_for_update(),
                                 TokenNotValidError())
    session = query.scalars().first()

    query = await __safe_execute(s, select(KeyOrm).filter(KeyOrm.id == session.key_id).with_for_update(),
                                 TokenNotValidError())
    key: KeyOrm = query.scalars().first()

    query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == key.account_id).with_for_update(),
                                 TokenNotValidError())
    account: AccountOrm = query.scalars().first()

    return ValidateByTokenData(session=session, key=key, account=account)


async def __check_access_to_update_training(s: AsyncSession, training_id: int, account_id: int):
    # e: AccessError, AccountNotFoundError
    query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == account_id).with_for_update())
    account: AccountOrm = query.scalars().first()
    if account.type == AccountType.ADMIN:
        return
    elif account.type == AccountType.EMPLOYEE:
        query = await s.execute(select(RoleOrm).options(joinedload(RoleOrm.trainings))
                                .join(RoleAndAccountOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                                .filter(RoleAndAccountOrm.account_id == account_id))
        roles = query.unique().scalars().all()
        training_ids = list(itertools.chain(*[[n.id for n in i.trainings] for i in roles]))
        if training_id not in training_ids:
            raise AccessError()
    elif account.type == AccountType.STUDENT:
        raise AccessError()
    else:
        raise TypeError()


async def __check_access_to_get_training(s: AsyncSession, training_id: int, account_id: int):
    # e: AccountNotFoundError, AccessError
    query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == account_id).with_for_update(),
                                 AccountNotFoundError())
    account: AccountOrm = query.scalars().first()
    if account.type == AccountType.ADMIN:
        return
    elif account.type == AccountType.EMPLOYEE:
        query = await s.execute(select(RoleOrm).options(joinedload(RoleOrm.trainings))
                                .join(RoleAndAccountOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                                .filter(RoleAndAccountOrm.account_id == account_id))
        roles = query.unique().scalars().all()
        training_ids = list(itertools.chain(*[[n.id for n in i.trainings] for i in roles]))
        if training_id not in training_ids:
            raise AccessError()
    elif account.type == AccountType.STUDENT:
        if account.training_id != training_id:
            raise AccessError()
    else:
        raise TypeError()


async def __generate_session_token(s: AsyncSession):
    query = await s.execute(select(SessionOrm).with_for_update())
    sessions = query.scalars().all()
    tokens = [i.token for i in sessions]
    while True:
        res = str(uuid.uuid4()).replace("-", "")[20:]
        if res not in tokens:
            break
    return res


async def __generate_access_key(s: AsyncSession):
    query = await s.execute(select(KeyOrm).with_for_update())
    keys = query.scalars().all()
    access_keys = [i.access_key for i in keys]
    while True:
        res = str(uuid.uuid4()).replace("-", "")[16:]
        if res not in access_keys:
            break
    return res


def __training_is_active(training: TrainingOrm) -> bool:
    return training.date_start and not training.date_end


async def __check_training_is_not_active(s: AsyncSession, training_id: int):
    # e: TrainingNotFoundError, TrainingIsActiveError
    query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update(),
                                 TrainingNotFoundError())
    training = query.scalars().first()
    if __training_is_active(training):
        raise TrainingIsActiveError()


@typechecked
async def check_training_is_not_active(token: Optional[str], training_id: int):
    # e: TokenNotValidError, UnknownError, TrainingNotFoundError, TrainingIsActiveError, AccessError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_get_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_is_not_active(s, training_id)
            await s.commit()
        except (TokenNotValidError, TrainingNotFoundError, TrainingIsActiveError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


async def __check_training_is_active(s: AsyncSession, training_id: int):
    # e: TrainingNotFoundError, TrainingIsNotActiveError
    query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update(),
                                 TrainingNotFoundError())
    training = query.scalars().first()
    if not __training_is_active(training):
        raise TrainingIsNotActiveError()


async def __check_training_has_not_students(s: AsyncSession, training_id: int):
    # e: TrainingHasStudentsError
    query = await s.execute(select(AccountOrm).filter(AccountOrm.type == AccountType.STUDENT,
                                                      AccountOrm.training_id == training_id).with_for_update())
    students = query.scalars().all()
    if students:
        raise TrainingHasStudentsError()


@typechecked()
async def check_training_has_not_students(token: str, training_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_get_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_has_not_students(s, training_id)
            await s.commit()
        except (TokenNotValidError, AccessError, TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def check_training_is_active(token: Optional[str], training_id: int):
    # e: TokenNotValidError, UnknownError, TrainingNotFoundError, TrainingIsNotActiveError, AccessError
    async with database.session_factory() as s:
        token_data = await __validate_by_token(s, token)
        try:
            try:
                await __check_access_to_get_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_is_active(s, training_id)
            await s.commit()
        except (TokenNotValidError, TrainingNotFoundError, TrainingIsNotActiveError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def token_validate(token: Optional[str]):
    # e: TokenNotValidError, UnknownError
    if not token:
        raise TokenNotValidError()
    async with database.session_factory() as s:
        try:
            await __validate_by_token(s, token)
            await s.commit()
        except TokenNotValidError as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def give_up_account(token: Optional[str]) -> GiveUpAccountData:
    # e: TokenNotValidError, UnknownError, AccessError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            token_data.account.first_name = "ADMIN"
            token_data.account.last_name = None
            token_data.account.patronymic = None
            token_data.account.email = None
            token_data.key.access_key = await __generate_access_key(s)
            token_data.key.is_first_log_in = True
            query = await s.execute(select(SessionOrm).filter(SessionOrm.key_id == token_data.key.id))
            sessions = query.scalars().all()
            for i in sessions:
                await s.delete(i)
            res = GiveUpAccountData(token_data.key.access_key)
            await s.commit()
            return res
        except (TokenNotValidError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def log_out(token: Optional[str]):
    # e: TokenNotValidError, UnknownError
    async with database.session_factory() as s:
        try:
            try:
                token_data = await __validate_by_token(s, token)
                await s.delete(token_data.session)
            except TokenNotValidError:
                pass
            await s.commit()
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_log_in_data_by_token(token: Optional[str], regenerate_access_key: bool = False) -> LogInData:
    # e: TokenNotValidError, UnknownError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if regenerate_access_key:
                token_data.key.access_key = await __generate_access_key(s)
            res = LogInData(token, token_data.key.is_first_log_in, token_data.key.access_key, token_data.account.type,
                            token_data.account.id)
            await s.commit()
            return res
        except TokenNotValidError as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def check_exist_of_access_key(access_key: str):
    # e: KeyNotFoundError, UnknownError
    async with database.session_factory() as s:
        try:
            query = await s.execute(select(KeyOrm).filter(KeyOrm.access_key == access_key).with_for_update())
            key = query.scalars().first()
            if not key:
                raise KeyNotFoundError
            await s.commit()
        except KeyNotFoundError as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def log_in(user_id: int, key: str) -> LogInData:
    # e: KeyNotFoundError, UnknownError
    async with database.session_factory() as s:
        try:
            query = await __safe_execute(s, select(KeyOrm).filter(KeyOrm.access_key == key).with_for_update(),
                                         KeyNotFoundError())
            key: KeyOrm = query.scalars().first()
            query = await s.execute(select(SessionOrm).filter(SessionOrm.user_id == user_id).with_for_update())
            c_session: Optional[SessionOrm] = query.scalars().first()
            if c_session:
                token_data = await __validate_by_token(s, c_session.token)
                await s.delete(token_data.session)
            is_first = key.is_first_log_in
            if is_first:
                key.access_key = await __generate_access_key(s)
                key.is_first_log_in = False
            token = await __generate_session_token(s)
            new_session = SessionOrm(key_id=key.id, token=token, user_id=user_id)
            s.add(new_session)
            query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == key.account_id)
                                         .with_for_update(), KeyNotFoundError())
            account: AccountOrm = query.scalars().first()
            res = LogInData(token=token, is_first=is_first, access_key=key.access_key, account_id=account.id,
                            account_type=account.type)
            await s.commit()
            return res
        except KeyNotFoundError as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_account_by_id(token: Optional[str], account_id: Optional[int] = None) -> AccountData:
    # e: TokenNotValidError, UnknownError, NotFoundError, AccessError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            account = token_data.account
            if account_id and account.id != account_id:
                account = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == account_id)
                                               .with_for_update())
            if token_data.account.type.value < account.type.value:
                raise AccessError()
            res = account_orm_to_account_data(account)
            await s.commit()
            return res
        except (TokenNotValidError, NotFoundError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_all_employees(token: Optional[str]) -> list[EmployeeData]:
    # e: TokenNotValidError, UnknownError, AccessError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError
            query = await s.execute(select(AccountOrm).options(joinedload(AccountOrm.roles))
                                    .filter(AccountOrm.type == AccountType.EMPLOYEE).order_by(AccountOrm.date_create))
            employees = query.unique().scalars().all()
            employees_data = []
            for i in employees:
                roles_data = [role_orm_to_role_data(r) for r in i.roles]
                employees_data.append(account_orm_to_employee_data(i, roles_data))
            await s.commit()
            return employees_data
        except (TokenNotValidError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_employee_by_id(token: Optional[str], employee_id: int) -> EmployeeData:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError
            if token_data.account.type == AccountType.EMPLOYEE and token_data.account.id != employee_id:
                raise AccessError
            query = await __safe_execute(s, select(AccountOrm).options(joinedload(AccountOrm.roles))
                                         .filter(AccountOrm.type == AccountType.EMPLOYEE,
                                                 AccountOrm.id == employee_id))
            employee = query.scalars().first()
            roles_data = [role_orm_to_role_data(r) for r in employee.roles]
            employee_data = account_orm_to_employee_data(employee, roles_data)
            await s.commit()
            return employee_data
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


async def __create_account(s: AsyncSession, account_type: AccountType, first_name: str,
                           last_name: Optional[str] = None, patronymic: Optional[str] = None,
                           email: Optional[str] = None, training_id: Optional[int] = None) -> CreatedAccountData:
    # e: TokenNotValidError, UnknownError, AccessError
    email_check(email)
    initials_check(first_name, last_name, patronymic)
    employee = AccountOrm(type=account_type, email=email, first_name=first_name, last_name=last_name,
                          patronymic=patronymic, training_id=training_id)
    s.add(employee)
    await s.flush()
    access_key = await __generate_access_key(s)
    key_orm = KeyOrm(account_id=employee.id, access_key=access_key)
    s.add(key_orm)
    await s.flush()
    return CreatedAccountData(employee.id, key_orm.access_key)


@typechecked
async def get_account_by_token(token: Optional[str]) -> AccountData | EmployeeData:
    # e: TokenNotValidError, UnknownError, NotFoundError, AccessError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            account_id = token_data.account.id
            account_type = token_data.account.type
            await s.commit()
            if account_type == AccountType.ADMIN:
                return await get_account_by_id(token, account_id)
            elif account_type == AccountType.EMPLOYEE:
                return await get_employee_by_id(token, account_id)
            elif account_type == AccountType.STUDENT:
                return await get_student_by_id(token, account_id)
            else:
                raise TypeError()
        except (TokenNotValidError, NotFoundError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def create_employee(token: Optional[str], first_name: str, last_name: Optional[str] = None,
                          patronymic: Optional[str] = None, email: Optional[str] = None) -> CreatedAccountData:
    # e: TokenNotValidError, UnknownError, AccessError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            res = await __create_account(s, AccountType.EMPLOYEE, first_name, last_name, patronymic, email)
            await s.commit()
            return res
        except (TokenNotValidError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def delete_employee(token: Optional[str], employee_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == employee_id).with_for_update())
            account_orm = query.scalars().first()
            await s.delete(account_orm)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def delete_student(token: Optional[str], student_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError()
            query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.type == AccountType.STUDENT)
                                         .filter(AccountOrm.id == student_id))
            student: AccountOrm = query.scalars().first()
            try:
                await __check_access_to_get_training(s, student.training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await s.delete(student)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def update_email_account(token: Optional[str], account_id: Optional[int] = None, email: Optional[str] = None):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError()
            if not account_id:
                account_id = token_data.account.id
            if token_data.account.type == AccountType.EMPLOYEE and account_id != token_data.account.id:
                raise AccessError()
            query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == account_id).with_for_update())
            account_orm = query.scalars().first()
            if email == '-':
                email = None
            email_check(email)
            account_orm.email = email
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def update_full_name_account(token: Optional[str], account_id: int, first_name: Optional[str] = None,
                                   last_name: Optional[str] = None, patronymic: Optional[str] = None):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError()
            query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == account_id).with_for_update())
            account_orm: AccountOrm = query.scalars().first()
            if token_data.account.type == AccountType.EMPLOYEE and account_orm.type != AccountType.STUDENT:
                raise AccessError()
            if token_data.account.type == AccountType.EMPLOYEE and account_orm.type == AccountType.STUDENT:
                try:
                    await __check_access_to_get_training(s, account_orm.training_id, token_data.account.id)
                except AccountNotFoundError:
                    raise TokenNotValidError()
            first_name, last_name, patronymic = (None if i == '-' else i for i in (first_name, last_name, patronymic))
            initials_check(first_name, last_name, patronymic)
            account_orm.first_name = first_name
            account_orm.last_name = last_name
            account_orm.patronymic = patronymic
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def add_role_to_employee(token: Optional[str], employee_id: int, role_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError (role), AccountNotFoundError (employee)
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            query = await __safe_execute(s, select(AccountOrm).filter(AccountOrm.id == employee_id),
                                         AccountNotFoundError())
            employee = query.scalars().first()
            await __safe_execute(s, select(RoleOrm).filter(RoleOrm.id == role_id), NotFoundError())
            if employee.type != AccountType.EMPLOYEE:
                raise ValueError("Only for employees")
            account_and_role = RoleAndAccountOrm(account_id=employee_id, role_id=role_id)
            s.add(account_and_role)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, AccountNotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def remove_role_from_employee(token: Optional[str], employee_id: int, role_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            query = await __safe_execute(s, select(RoleAndAccountOrm).filter(RoleAndAccountOrm.role_id == role_id)
                                         .filter(RoleAndAccountOrm.account_id == employee_id).with_for_update())
            account_and_role = query.scalars().first()
            await s.delete(account_and_role)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


# Roles
@typechecked
async def create_role(token: Optional[str], name: str) -> RoleData:
    # e: TokenNotValidError, UnknownError, AccessError, RoleNotUniqueNameError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            role_name_check(name)
            new_role = RoleOrm(name=name)
            try:
                s.add(new_role)
                await s.flush()
                res = role_orm_to_role_data(new_role)
                await s.commit()
            except IntegrityError:
                raise RoleNotUniqueNameError()
            return res
        except (TokenNotValidError, AccessError, RoleNotUniqueNameError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def delete_role(token: Optional[str], role_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            query = await __safe_execute(s, select(RoleOrm).filter(RoleOrm.id == role_id).with_for_update())
            role = query.scalars().first()
            await s.delete(role)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def update_role(token: Optional[str], role_id: int, name: str):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, RoleNotUniqueNameError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            query = await __safe_execute(s, select(RoleOrm).filter(RoleOrm.id == role_id).with_for_update())
            role = query.scalars().first()
            role_name_check(name)
            role.name = name
            try:
                await s.commit()
            except IntegrityError:
                raise RoleNotUniqueNameError()
        except (TokenNotValidError, AccessError, NotFoundError, RoleNotUniqueNameError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_all_roles(token: Optional[str], account_id: Optional[int] = None) -> list[RoleData]:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError()
            if not account_id:
                account_id = token_data.account.id
            if token_data.account.type == AccountType.EMPLOYEE and account_id != token_data.account.id:
                raise AccessError()
            query = await __safe_execute(s, select(AccountOrm).options(joinedload(AccountOrm.roles))
                                         .filter(AccountOrm.id == account_id))
            account = query.unique().scalars().first()
            if account.type == AccountType.EMPLOYEE:
                res = [role_orm_to_role_data(i) for i in account.roles]
                res.sort(key=lambda x: x.date_create)
            else:
                query = await s.execute(select(RoleOrm).order_by(RoleOrm.date_create).with_for_update())
                res = [role_orm_to_role_data(i) for i in query.scalars().all()]
            await s.commit()
            return res
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_role_by_id(token: Optional[str], role_id: int) -> RoleData:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError
            if token_data.account.type == AccountType.EMPLOYEE:
                query = await __safe_execute(s, select(AccountOrm).options(joinedload(AccountOrm.roles))
                                             .filter(AccountOrm.id == token_data.account.id), TokenNotValidError())
                account = query.unique().scalars().first()
                allowed_role_ids = [i.id for i in account.roles]
                if role_id not in allowed_role_ids:
                    raise AccessError()
            query = await __safe_execute(s, select(RoleOrm).options(joinedload(RoleOrm.accounts))
                                         .options(joinedload(RoleOrm.trainings)).filter(RoleOrm.id == role_id))
            role = query.unique().scalars().first()
            trainings = [training_orm_to_training_data(i, None, None) for i in role.trainings]
            accounts = [account_orm_to_account_data(i) for i in role.accounts]
            role_data = role_orm_to_role_data(role, trainings, accounts)
            await s.commit()
            return role_data
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def add_training_to_role(token: Optional[str], role_id: int, training_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError (role), TrainingNotFoundError (training)
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id)
                                 .with_for_update(), TrainingNotFoundError())
            await __safe_execute(s, select(RoleOrm).filter(RoleOrm.id == role_id).with_for_update())
            training_and_role = TrainingAndRoleOrm(training_id=training_id, role_id=role_id)
            s.add(training_and_role)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingNotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def remove_training_from_role(token: Optional[str], role_id: int, training_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.ADMIN:
                raise AccessError()
            query = await __safe_execute(s, select(TrainingAndRoleOrm).filter(TrainingAndRoleOrm.role_id == role_id)
                                         .filter(TrainingAndRoleOrm.training_id == training_id).with_for_update())
            training_and_role = query.scalars().first()
            await s.delete(training_and_role)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


# Trainings
@typechecked
async def create_training(token: Optional[str], name: str, start_text: Optional[str] = None,
                          html_start_text: Optional[str] = None, role_id: Optional[int] = None) -> TrainingData:
    # e: TokenNotValidError, UnknownError, AccessError, NotChooseRoleError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError()
            if token_data.account.type == AccountType.EMPLOYEE:
                query = await __safe_execute(s, select(AccountOrm).options(joinedload(AccountOrm.roles))
                                             .filter(AccountOrm.id == token_data.account.id), TokenNotValidError())
                account = query.unique().scalars().first()
                allowed_role_ids = [i.id for i in account.roles]
                if role_id is None and len(allowed_role_ids) == 1:
                    role_id = allowed_role_ids[0]
                if role_id is None:
                    raise NotChooseRoleError()
                if role_id not in allowed_role_ids:
                    raise AccessError("The employee does not have this role")
            training_name_check(name)
            new_training = TrainingOrm(name=name)
            if bool(start_text) != bool(html_start_text):
                raise ValueError("The start_text has a value, but html_start_text does not, or vice versa")
            elif start_text and html_start_text:
                new_training.start_text = start_text
                new_training.html_start_text = html_start_text
            s.add(new_training)
            await s.flush()
            training_data = training_orm_to_training_data(new_training, None, None)
            if role_id:
                training_and_role = TrainingAndRoleOrm(role_id=role_id, training_id=new_training.id)
                s.add(training_and_role)
            await s.commit()
            return training_data
        except (TokenNotValidError, AccessError, NotChooseRoleError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_all_trainings(token: Optional[str]):
    # e: TokenNotValidError, UnknownError, AccessError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type not in [AccountType.ADMIN, AccountType.EMPLOYEE]:
                raise AccessError()
            if token_data.account.type == AccountType.EMPLOYEE:
                await __safe_execute(s, select(RoleOrm).join(RoleAndAccountOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                                     .filter(RoleAndAccountOrm.account_id == token_data.account.id), AccessError())
                query = await s.execute(select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                        .join(TrainingAndRoleOrm, TrainingOrm.id == TrainingAndRoleOrm.training_id)
                                        .join(RoleOrm, TrainingAndRoleOrm.role_id == RoleOrm.id)
                                        .join(RoleAndAccountOrm, RoleOrm.id == RoleAndAccountOrm.role_id)
                                        .filter(RoleAndAccountOrm.account_id == token_data.account.id)
                                        .order_by(TrainingOrm.date_create))
            else:
                query = await s.execute(select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                        .order_by(TrainingOrm.date_create))
            trainings = query.unique().scalars().all()
            trainings_data = []
            for i in trainings:
                students_data = [account_orm_to_student_data(n, None, None) for n in i.students]
                trainings_data.append(training_orm_to_training_data(i, students_data, None))
            await s.commit()
            return trainings_data
        except (TokenNotValidError, AccessError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_training_by_id(token: Optional[str], training_id: int) -> TrainingData:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_get_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            query = await __safe_execute(s, select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                         .options(joinedload(TrainingOrm.levels)).filter(TrainingOrm.id == training_id))
            training = query.unique().scalars().first()
            students_data = [account_orm_to_student_data(i, None, None) for i in training.students]
            levels_data = [level_orm_to_level_data(i, None, None, None) for i in training.levels]
            training_data = training_orm_to_training_data(training, students_data, levels_data)
            await s.commit()
            return training_data
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def update_start_msg_training(token: Optional[str], training_id: int, msg: list[Message]):
    # e: TokenNotValidError, UnknownError, AccessError, TrainingNotFoundError, TrainingIsActiveError,
    # TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update())
            training = query.scalars().first()
            await __check_training_is_not_active(s, training_id)
            await __check_training_has_not_students(s, training_id)
            training.message = msg
            await s.commit()
        except (TokenNotValidError, AccessError, TrainingNotFoundError, TrainingIsActiveError,
                TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def delete_training(token: Optional[str], training_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingIsActiveError, TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update())
            training = query.scalars().first()
            try:
                await __check_training_is_not_active(s, training_id)
                await __check_training_has_not_students(s, training_id)
            except TrainingNotFoundError:
                raise NotFoundError()
            await s.delete(training)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingIsActiveError, TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def update_name_training(token: Optional[str], training_id: int, name: Optional[str] = None):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingIsActiveError, TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update())
            training = query.scalars().first()
            try:
                await __check_training_is_not_active(s, training_id)
                await __check_training_has_not_students(s, training_id)
            except TrainingNotFoundError:
                raise NotFoundError()
            training.name = name
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingIsActiveError, TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def start_training(token: Optional[str], training_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingIsEmptyError,
    # TrainingAlreadyHasThisStateError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            query = await __safe_execute(s, select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                         .options(joinedload(TrainingOrm.levels)).filter(TrainingOrm.id == training_id))
            training = query.unique().scalars().first()
            if len(training.levels) == 0:
                raise TrainingIsEmptyError()
            if __training_is_active(training):
                raise TrainingAlreadyHasThisStateError()
            training.date_start = get_current_time()
            training.date_end = None
            for student in training.students:
                await s.delete(student)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingIsEmptyError,
                TrainingAlreadyHasThisStateError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def stop_training(token: Optional[str], training_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingAlreadyHasThisStateError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update())
            training = query.scalars().first()
            if not (training.date_start and not training.date_end):
                raise TrainingAlreadyHasThisStateError()
            training.date_end = get_current_time()
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingAlreadyHasThisStateError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def clear_training(token: Optional[str], training_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingIsActiveError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update())
            query = await __safe_execute(s, select(TrainingOrm).options(joinedload(TrainingOrm.students))
                                         .options(joinedload(TrainingOrm.levels)).filter(TrainingOrm.id == training_id))
            training = query.unique().scalars().first()
            await __check_training_is_not_active(s, training_id)
            training.date_start, training.date_end = None, None
            for student in training.students:
                await s.delete(student)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingIsActiveError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


# Levels
@typechecked
async def create_level(token: Optional[str], level_type: str, training_id: int, title: str, messages: list[Message]):
    # e: TokenNotValidError, UnknownError, AccessError, TrainingNotFoundError, TrainingIsActiveError,
    # TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_is_not_active(s, training_id)
            await __check_training_has_not_students(s, training_id)
            query = await s.execute(select(LevelOrm).filter(LevelOrm.training_id == training_id,
                                                            LevelOrm.next_level_id == None).with_for_update())
            last_level = query.scalars().first()
            last_level_id = last_level.id if last_level else None
            level = LevelOrm(previous_level_id=last_level_id, training_id=training_id, type=level_type,
                             title=title, messages=messages)
            s.add(level)
            await s.flush()
            if last_level:
                last_level.next_level_id = level.id
            await s.commit()
        except (TokenNotValidError, AccessError, TrainingNotFoundError, TrainingIsActiveError,
                TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def update_content_level_by_id(token: Optional[str], level_type: str, level_id: int, messages: list[Message]):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingNotFoundError, TrainingIsActiveError,
    # TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            query = await __safe_execute(s, select(LevelOrm).filter(LevelOrm.id == level_id).with_for_update())
            level = query.scalars().first()
            try:
                await __check_access_to_update_training(s, level.training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_is_not_active(s, level.training_id)
            await __check_training_has_not_students(s, level.training_id)
            level.messages = messages
            level.type = level_type
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingNotFoundError, TrainingIsActiveError,
                TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def update_title_level_by_id(token: Optional[str], level_id: int, title: str):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingNotFoundError, TrainingIsActiveError,
    # TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            query = await __safe_execute(s, select(LevelOrm).filter(LevelOrm.id == level_id).with_for_update())
            level = query.scalars().first()
            try:
                await __check_access_to_update_training(s, level.training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_is_not_active(s, level.training_id)
            await __check_training_has_not_students(s, level.training_id)
            level.title = title
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingNotFoundError, TrainingIsActiveError,
                TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def delete_level_by_id(token: Optional[str], level_id: int):
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingNotFoundError, TrainingIsActiveError,
    # TrainingHasStudentsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            query = await __safe_execute(s, select(LevelOrm).filter(LevelOrm.id == level_id).with_for_update())
            level = query.scalars().first()
            try:
                await __check_access_to_update_training(s, level.training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_is_not_active(s, level.training_id)
            await __check_training_has_not_students(s, level.training_id)
            if level.next_level_id:
                query = await s.execute(select(LevelOrm).filter(LevelOrm.id == level.next_level_id).with_for_update())
                next_level = query.scalars().first()
                next_level.previous_level_id = level.previous_level_id
            if level.previous_level_id:
                query = await s.execute(
                    select(LevelOrm).filter(LevelOrm.id == level.previous_level_id).with_for_update())
                previous_level = query.scalars().first()
                previous_level.next_level_id = level.next_level_id
            await s.delete(level)
            await s.commit()
        except (TokenNotValidError, AccessError, NotFoundError, TrainingNotFoundError, TrainingIsActiveError,
                TrainingHasStudentsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


async def __get_levels_sorted(s: AsyncSession, training_id: int) -> list[LevelOrm]:
    # e: TrainingNotFoundError
    await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update(),
                         TrainingNotFoundError())
    query = await s.execute(select(LevelOrm).options(joinedload(LevelOrm.training))
                            .filter(LevelOrm.training_id == training_id))
    levels = query.unique().scalars().all()
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
async def get_levels_by_training(token: Optional[str], training_id: int) -> list[LevelData]:
    # e: TokenNotValidError, UnknownError, AccessError, TrainingNotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            levels: Any = await __get_levels_sorted(s, training_id)
            levels_data = []
            for i in levels:
                training_data = training_orm_to_training_data(i.training, None, None)
                levels_data.append(level_orm_to_level_data(i, levels.index(i) + 1, training_data, None))
            await s.commit()
            return levels_data
        except (TokenNotValidError, AccessError, TrainingNotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_level_by_id(token: Optional[str], level_id: int) -> LevelData:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            query = await __safe_execute(s, select(LevelOrm).options(joinedload(LevelOrm.training))
                                         .options(joinedload(LevelOrm.answers)).filter(LevelOrm.id == level_id))
            level = query.unique().scalars().first()
            levels: Any = await __get_levels_sorted(s, level.training_id)
            index = next((i for i in range(len(levels)) if levels[i].id == level_id), None)
            if index is None:
                raise ValueError
            try:
                await __check_access_to_update_training(s, level.training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            training_data = training_orm_to_training_data(level.training, None, None)
            answers = [level_answer_orm_to_level_answer_data(i, None, None) for i in level.answers]
            level_data = level_orm_to_level_data(level, index + 1, training_data, answers=answers)
            await s.commit()
            return level_data
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


# Students
@typechecked
async def create_student(token: Optional[str], training_id: int, first_name: str, last_name: Optional[str] = None,
                         patronymic: Optional[str] = None) -> CreatedAccountData:
    # e: TokenNotValidError, UnknownError, AccessError, TrainingIsNotActiveError, TrainingNotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            try:
                await __check_access_to_update_training(s, training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            await __check_training_is_active(s, training_id)
            res = await __create_account(s, AccountType.STUDENT, first_name, last_name, patronymic,
                                         training_id=training_id)
            await s.commit()
            return res
        except (TokenNotValidError, AccessError, TrainingIsNotActiveError, TrainingNotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_student_by_id(token: Optional[str], student_id: int) -> StudentData:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            query = await __safe_execute(s, select(AccountOrm).options(joinedload(AccountOrm.training))
                                         .options(joinedload(AccountOrm.answers))
                                         .filter(AccountOrm.type == AccountType.STUDENT, AccountOrm.id == student_id))
            student = query.unique().scalars().first()
            if student.type != AccountType.STUDENT:
                raise ValueError()
            if token_data.account.type == AccountType.STUDENT and token_data.account.id != student_id:
                raise AccessError
            if token_data.account.type == AccountType.EMPLOYEE:
                try:
                    await __check_access_to_update_training(s, student.training_id, token_data.account.id)
                except AccountNotFoundError:
                    raise TokenNotValidError()
            training = training_orm_to_training_data(student.training, None, None)
            answers = [level_answer_orm_to_level_answer_data(i, None, None) for i in student.answers]
            res = account_orm_to_student_data(student, training=training, answers=answers)
            await s.commit()
            return res
        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_all_student_progresses(token: Optional[str], training_id: int) -> list[StudentProgressData]:
    # e: TokenNotValidError, UnknownError, AccessError, TrainingNotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type == AccountType.EMPLOYEE:
                try:
                    await __check_access_to_update_training(s, training_id, token_data.account.id)
                except AccountNotFoundError:
                    raise TokenNotValidError()
            query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id).with_for_update(),
                                         TrainingNotFoundError())
            training = query.scalars().first()
            query = await s.execute(select(AccountOrm).options(joinedload(AccountOrm.training))
                                    .options(joinedload(AccountOrm.answers).joinedload(LevelAnswerOrm.level))
                                    .filter(AccountOrm.type == AccountType.STUDENT)
                                    .filter(AccountOrm.training_id == training_id))
            students = query.unique().scalars().all()
            is_access = __training_is_active(training)
            all_levels: Any = await __get_levels_sorted(s, training_id)
            res = []
            for student in students:
                level_ids_by_answers = [i.level_id for i in student.answers]
                not_completed_levels = [i for i in all_levels if i.id not in level_ids_by_answers]
                progress_state = StudentProgressState.COMPLETED
                current_level = None
                if len(not_completed_levels) == len(all_levels):
                    progress_state = StudentProgressState.CREATED
                    current_level = not_completed_levels[0]
                elif not_completed_levels:
                    progress_state = StudentProgressState.LEARNING
                    current_level = not_completed_levels[0]
                answers_data = [level_answer_orm_to_level_answer_data(i, None, None) for i in student.answers]
                student_data = account_orm_to_student_data(student, None, None)
                if current_level:
                    current_level_data = level_orm_to_level_data(current_level, None, None, None)
                else:
                    current_level_data = None
                all_level = [level_orm_to_level_data(i, None, None, None) for i in all_levels]
                training_data = training_orm_to_training_data(student.training, None, all_level)
                result = StudentProgressData(is_access=is_access, student=student_data, progress_state=progress_state,
                                             current_level=current_level_data, answers=answers_data,
                                             training=training_data)
                res.append(result)
            await s.commit()
            return res
        except (TokenNotValidError, AccessError, TrainingNotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


@typechecked
async def get_student_progress(token: Optional[str], student_id: Optional[int] = None) -> StudentProgressData:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if not student_id:
                student_id = token_data.account.id
            if token_data.account.type == AccountType.STUDENT and student_id != token_data.account.id:
                raise AccessError()
            query = await __safe_execute(s, select(AccountOrm).options(joinedload(AccountOrm.training))
                                         .options(joinedload(AccountOrm.answers).joinedload(LevelAnswerOrm.level))
                                         .filter(AccountOrm.type == AccountType.STUDENT, AccountOrm.id == student_id))
            student = query.scalars().first()
            if token_data.account.type == AccountType.EMPLOYEE:
                try:
                    await __check_access_to_update_training(s, student.training_id, token_data.account.id)
                except AccountNotFoundError:
                    raise TokenNotValidError()
            is_access = __training_is_active(student.training)
            all_levels: Any = await __get_levels_sorted(s, student.training_id)

            level_ids_by_answers = [i.level_id for i in student.answers]
            not_completed_levels = [i for i in all_levels if i.id not in level_ids_by_answers]
            progress_state = StudentProgressState.COMPLETED
            current_level = None
            if len(not_completed_levels) == len(all_levels):
                progress_state = StudentProgressState.CREATED
                current_level = not_completed_levels[0]
            elif not_completed_levels:
                progress_state = StudentProgressState.LEARNING
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
            await s.commit()
            return res

        except (TokenNotValidError, AccessError, NotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


def __level_type_to_r_level_type(it: str) -> RLevelType:
    if it == LevelType.INFO:
        return RLevelType.INFO
    elif it == LevelType.CONTROL:
        return RLevelType.CONTROL


def __training_state_to_r_training_state(is_active: bool) -> RTrainingState:
    if is_active:
        return RTrainingState.ACTIVE
    return RTrainingState.INACTIVE


def __student_state_to_r_student_state(student: AccountOrm, levels: list[LevelOrm]) -> RStudentState:
    level_ids_by_answers = [i.level_id for i in student.answers]
    not_completed_levels = [i for i in levels if i.id not in level_ids_by_answers]
    progress_state = RStudentState.COMPLETED
    if len(not_completed_levels) == len(levels):
        progress_state = RStudentState.CREATED
    elif not_completed_levels:
        progress_state = RStudentState.LEARNING
    return progress_state


# noinspection PyTypeChecker
@typechecked
async def get_training_report(token: Optional[str], training_id: int) -> TrainingReportData:
    # e: TokenNotValidError, UnknownError, AccessError, TrainingNotFoundError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type == AccountType.EMPLOYEE:
                try:
                    await __check_access_to_update_training(s, training_id, token_data.account.id)
                except AccountNotFoundError:
                    raise TokenNotValidError()
            levels = await __get_levels_sorted(s, training_id)
            query = await __safe_execute(s, select(TrainingOrm).filter(TrainingOrm.id == training_id)
                                         .with_for_update(), TrainingNotFoundError())
            training: TrainingOrm = query.scalars().first()
            await s.execute(select(AccountOrm).filter(AccountOrm.training_id == training_id)
                            .with_for_update(), None)
            query = await s.execute(select(AccountOrm)
                                    .options(joinedload(AccountOrm.answers).joinedload(LevelAnswerOrm.level))
                                    .filter(AccountOrm.training_id == training_id))
            students: list[AccountOrm] = query.unique().scalars().all()
            level_answers = list(itertools.chain(*[i.answers for i in students]))
            level_answers.sort(key=lambda x: x.date_create)

            training_state = __training_state_to_r_training_state(__training_is_active(training))
            training_rt = training_orm_to_training_rt(training, training_state)
            levels_rt = []
            for i in range(len(levels)):
                level_type = __level_type_to_r_level_type(levels[i].type)
                levels_rt.append(level_orm_to_level_rt(levels[i], i + 1, level_type))
            students_rt = []
            for student in students:
                level_ids_by_answers = [i.level_id for i in student.answers]
                progress_percent = len(level_ids_by_answers) / len(levels)
                student_state = __student_state_to_r_student_state(student, levels)
                students_rt.append(account_orm_to_student_rt(student, student_state, progress_percent))
            answers_rt = []
            for answer in level_answers:
                answers_rt.append(level_answer_orm_to_answer_rt(answer, answer.level, training_id))
            report_date_create = datetime.utcnow()
            report_date_create_timestamp = int(report_date_create.timestamp())
            report_rt = ReportRT(date_create=report_date_create)
            await s.commit()
            date = get_date_str(report_date_create_timestamp, DateFormat.FORMAT_FULL_2)
            tables = [*answers_rt, *levels_rt, *students_rt, training_rt, report_rt]
            table_types = [AnswerRT, LevelRT, StudentRT, TrainingRT, ReportRT]
            report_file = await xlsx_engine.create_xlsx(f"Report_{training_id}_{date}", table_types, tables)
            return TrainingReportData(report_file, report_date_create_timestamp, training_id)
        except (TokenNotValidError, AccessError, TrainingNotFoundError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()


# LevelAnswer
@typechecked
async def create_level_answer(token: Optional[str], level_id: int,
                              answer_option_ids: Optional[list[int]] = None) -> LevelAnswerData:
    # e: TokenNotValidError, UnknownError, AccessError, NotFoundError, TrainingIsNotActiveError,
    # LevelAnswerAlreadyExistsError
    async with database.session_factory() as s:
        try:
            token_data = await __validate_by_token(s, token)
            if token_data.account.type != AccountType.STUDENT:
                raise AccessError
            query = await __safe_execute(s, select(LevelOrm).filter(LevelOrm.id == level_id).with_for_update())
            level = query.scalars().first()
            try:
                await __check_access_to_get_training(s, level.training_id, token_data.account.id)
            except AccountNotFoundError:
                raise TokenNotValidError()
            try:
                await __check_training_is_active(s, level.training_id)
            except TrainingNotFoundError:
                raise NotFoundError()
            query = await s.execute(select(LevelAnswerOrm)
                                    .filter(LevelAnswerOrm.level_id == level_id,
                                            LevelAnswerOrm.account_id == token_data.account.id)
                                    .with_for_update())
            exist_level_answer = query.scalars().first()
            if exist_level_answer:
                raise LevelAnswerAlreadyExistsError()

            if level.type == LevelType.CONTROL and answer_option_ids:
                msg: Message = level.messages[0]
                is_correct = msg.poll.correct_option_id == answer_option_ids[0]
                level_answer = LevelAnswerOrm(account_id=token_data.account.id, level_id=level_id,
                                              is_correct=is_correct,
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
        except (TokenNotValidError, AccessError, NotFoundError, TrainingIsNotActiveError,
                LevelAnswerAlreadyExistsError) as e:
            await s.rollback()
            raise e
        except SQLAlchemyError as e:
            await s.rollback()
            logger.error(f"SQLAlchemyError occurred: {str(e)}")
            raise UnknownError()
        except Exception as e:
            await s.rollback()
            logger.error(f"Exception occurred: {str(e)}")
            raise UnknownError()
