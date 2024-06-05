from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import TokenNotValidError, AccessError
from data.asvttk_service.models import AccountType

from handlers.handlers_utils import get_token
from src import strings

router = Router()


@router.message()
async def help_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        account = await service.get_account_by_id(token)
        if account.type == AccountType.ADMIN:
            await msg.answer(strings.HELP__ADMIN)
        else:
            await msg.answer("Хз, как это показать...")
    except TokenNotValidError:
        await msg.answer(strings.HELP__NO_AUTHORIZATION)
        return
