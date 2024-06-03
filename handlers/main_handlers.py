from aiogram import Router
from aiogram.filters import StateFilter, CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src import strings, commands
from custom_storage import TOKEN
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import KeyNotFoundError
from data.asvttk_service.models import AccountType
from src.states import MainStates
from src.utils import key_link, get_token_from_state

router = Router()


@router.message(Command(commands.START))
async def start_handler(msg: Message, state: FSMContext, command: CommandObject):
    if not command.args:
        await msg.answer(strings.LOG_IN__NO_ACCESS_KEY)
        return
    user_id = msg.from_user.id
    try:
        log_in_data = await service.log_in(user_id, key=command.args)
        if log_in_data.account_type == AccountType.ADMIN:
            await state.set_state(MainStates.ADMIN)
        elif log_in_data.account_type == AccountType.EMPLOYEE:
            await state.set_state(MainStates.EMPLOYEE)
        elif log_in_data.account_type == AccountType.STUDENT:
            await state.set_state(MainStates.STUDENT)
        await state.update_data({TOKEN: log_in_data.token})
        if log_in_data.is_first:
            await msg.answer(strings.LOG_IN__SUCCESS__FIRST.format(key=log_in_data.access_key,
                                                                   key_link=key_link(log_in_data.access_key)))
        else:
            await msg.answer(strings.LOG_IN__SUCCESS)
    except KeyNotFoundError:
        await msg.answer(strings.LOG_IN__ACCOUNT_NOT_FOUND)


@router.message(StateFilter(None), Command(commands.HELP))
@router.message(MainStates(), Command(commands.HELP))
async def help_handler(msg: Message, state: FSMContext):
    token = await get_token_from_state(state)
    if not token:
        await msg.answer(strings.HELP__NO_AUTHORIZATION)
        return
    account = await service.get_account_by_id(token)
    if account.type.ADMIN:
        await msg.answer(strings.HELP__ADMIN)
    else:
        await msg.answer("Хз, как это показать...")
