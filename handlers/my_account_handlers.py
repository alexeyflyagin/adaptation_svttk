from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from data.asvttk_service.exceptions import TokenNotValidError, AccessError
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.models import AccountType
from data.asvttk_service.types import AccountData, EmployeeData
from handlers.handlers_utils import get_token, token_not_valid_error
from src import commands, strings
from src.states import MainStates
from src.strings import field, code, italic
from src.utils import get_account_type_str, show

router = Router()


@router.message(MainStates.ADMIN, Command(commands.MYACCOUNT))
@router.message(MainStates.EMPLOYEE, Command(commands.MYACCOUNT))
@router.message(MainStates.STUDENT, Command(commands.MYACCOUNT))
async def my_account_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        await show_my_account(token, msg)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


async def show_my_account(token: str, msg: Message, edited_msg_id: Optional[int] = None, is_answer: bool = True):
    account: AccountData | EmployeeData
    account = await service.get_account_by_token(token)
    if account.type == AccountType.ADMIN:
        text = strings.MY_ACCOUNT__ADMIN.format(
            last_name=field(account.last_name),
            first_name=field(account.first_name),
            patronymic=field(account.patronymic),
            account_type=get_account_type_str(account.type),
        )
    elif account.type == AccountType.EMPLOYEE:
        try:
            trainings = await service.get_all_trainings(token)
            trainings_field = field(" | ".join([code(i.name) for i in trainings]))
        except AccessError:
            trainings_field = italic(strings.TRAININGS__UNAVAILABLE)
        text = strings.MY_ACCOUNT__EMPLOYEE.format(
            last_name=field(account.last_name),
            first_name=field(account.first_name),
            patronymic=field(account.patronymic),
            account_type=get_account_type_str(account.type),
            roles=field(" | ".join([code(i.name) for i in account.roles])),
            trainings=trainings_field,
        )
    else:
        raise ValueError
    await show(msg, text, is_answer, edited_msg_id)
