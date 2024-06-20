from aiogram import Router
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import TokenNotValidError
from data.asvttk_service.models import AccountType

from handlers.handlers_utils import get_token
from src import strings
from src.states import MainStates
from src.utils import show

router = Router()


@router.message(MainStates.ADMIN)
@router.message(MainStates.EMPLOYEE)
@router.message(StateFilter(None))
async def help_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type in [ContentType.PINNED_MESSAGE]:
        return
    try:
        await show_help(token, msg)
    except TokenNotValidError:
        await msg.answer(strings.HELP__NO_AUTHORIZATION)
        return


@router.message(MainStates.STUDENT)
async def other_handler(msg: Message, state: FSMContext):
    await msg.delete()


async def show_help(token: str, msg: Message, is_answer: bool = True):
    await service.token_validate(token)
    account = await service.get_account_by_id(token)
    if account.type == AccountType.ADMIN:
        text = strings.HELP__ADMIN
    elif account.type == AccountType.EMPLOYEE:
        text = strings.HELP__EMPLOYEE
    else:
        raise ValueError()
    await show(msg, text, is_answer)
