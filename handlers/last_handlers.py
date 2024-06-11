from aiogram import Router
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import TokenNotValidError
from data.asvttk_service.models import AccountType

from handlers.handlers_utils import get_token
from src import strings

router = Router()


@router.message()
async def help_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type in [ContentType.PINNED_MESSAGE]:
        return
    try:
        await service.token_validate(token)
        account = await service.get_account_by_id(token)
        text = "Хз, как это показать..."
        if account.type == AccountType.ADMIN:
            text = strings.HELP__ADMIN
        if account.type == AccountType.EMPLOYEE:
            text = strings.HELP__EMPLOYEE
        await msg.answer(text)
    except TokenNotValidError:
        await msg.answer(strings.HELP__NO_AUTHORIZATION)
        return
