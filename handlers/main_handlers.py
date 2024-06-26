import asyncio

from aiogram import Router
from aiogram.filters import CommandObject, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from custom_storage import TOKEN
from data.asvttk_service.models import AccountType
from handlers.authorization_handlers import show_log_out_warning, log_in
from handlers.handlers_utils import reset_state, delete_msg, add_additional_msg_id, get_token, token_not_valid_error, \
    unknown_error
from src import strings, commands
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import KeyNotFoundError, TokenNotValidError, UnknownError
from src.states import RoleCreateStates, RoleRenameStates, EmployeeCreateStates, EmployeeEditEmailStates, \
    TrainingCreateStates, EmployeeEditFullNameStates, TrainingEditNameStates, LevelCreateStates, \
    TrainingStartEditStates, LevelEditStates, StudentCreateState, MainStates, MyAccountEditStates

router = Router()


@router.message(MainStates(), Command(commands.START))
@router.message(StateFilter(None), Command(commands.START))
async def start_handler(msg: Message, state: FSMContext, command: CommandObject):
    access_key = command.args
    state_data = await state.get_data()
    token = state_data.get(TOKEN, None)
    if not access_key:
        bot_msg = await msg.answer(strings.LOG_IN__NO_ACCESS_KEY)
        if token:
            await asyncio.sleep(3)
            await delete_msg(msg.bot, msg.chat.id, msg.message_id)
            await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
        else:
            await delete_msg(msg.bot, msg.chat.id, msg.message_id)
            await add_additional_msg_id(state, bot_msg.message_id)
        return
    try:
        await service.check_exist_of_access_key(access_key)
        try:
            if token is None:
                raise TokenNotValidError()
            account = await service.get_account_by_token(token)
            await delete_msg(msg.bot, msg.chat.id, msg.message_id)
            if account.type == AccountType.STUDENT:
                await show_log_out_warning(token, msg, strings.LOG_IN__WARNING__STUDENT, access_key)
                return
            else:
                await show_log_out_warning(token, msg, strings.LOG_OUT__WARNING, access_key)
                return
        except TokenNotValidError:
            pass
        await log_in(msg, msg.from_user.id, state, access_key)
    except KeyNotFoundError:
        bot_msg = await msg.answer(strings.LOG_IN__ACCOUNT_NOT_FOUND)
        if token:
            await asyncio.sleep(3)
            await delete_msg(msg.bot, msg.chat.id, msg.message_id)
            await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
        else:
            await delete_msg(msg.bot, msg.chat.id, msg.message_id)
            await add_additional_msg_id(state, bot_msg.message_id)
    await delete_msg(msg.bot, msg.chat.id, msg.message_id)


@router.message(RoleCreateStates(), Command(commands.CANCEL))
@router.message(RoleRenameStates(), Command(commands.CANCEL))
@router.message(EmployeeEditEmailStates(), Command(commands.CANCEL))
@router.message(TrainingEditNameStates(), Command(commands.CANCEL))
@router.message(EmployeeEditFullNameStates(), Command(commands.CANCEL))
@router.message(EmployeeCreateStates(), Command(commands.CANCEL))
@router.message(TrainingCreateStates(), Command(commands.CANCEL))
@router.message(LevelCreateStates(), Command(commands.CANCEL))
@router.message(TrainingStartEditStates(), Command(commands.CANCEL))
@router.message(StudentCreateState(), Command(commands.CANCEL))
@router.message(LevelEditStates(), Command(commands.CANCEL))
@router.message(MyAccountEditStates(), Command(commands.CANCEL))
async def cancel_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        await reset_state(state)
        await msg.answer(strings.ACTION_CANCELED)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)
