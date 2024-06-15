import asyncio

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandObject, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers import admin_roles_handlers, handlers_utils, last_handlers, admin_employees_handlers, trainings_handlers
from handlers.handlers_utils import reset_state
from handlers.last_handlers import help_handler
from src import strings, commands
from custom_storage import TOKEN
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import KeyNotFoundError
from src.states import RoleCreateStates, RoleRenameStates, EmployeeCreateStates, EmployeeEditEmailStates, \
    TrainingCreateStates, EmployeeEditFullNameStates, TrainingEditNameStates, LevelCreateStates, MainStates
from src.utils import get_access_key_link, START_SESSION_MSG_ID

router = Router()
router.include_routers(trainings_handlers.router)
router.include_routers(admin_roles_handlers.router)
router.include_routers(admin_employees_handlers.router)
router.include_routers(last_handlers.router)


class LogInDataCD(CallbackData, prefix='log_in_data'):
    first_name: str
    access_key: str
    action: int

    class Action:
        PIN = 0


def get_log_in_data_keyboard(first_name: str, access_key: str, has_pin: bool = True, has_log_in: bool = True):
    kbb = InlineKeyboardBuilder()
    if has_pin:
        btn_pin_data = LogInDataCD(first_name=first_name, access_key=access_key, action=LogInDataCD.Action.PIN)
        kbb.add(InlineKeyboardButton(text=strings.BTN_PIN, callback_data=btn_pin_data.pack()))
    if has_log_in:
        url = get_access_key_link(access_key=access_key)
        kbb.add(InlineKeyboardButton(text=strings.BTN_LOG_IN, url=url))
    kbb.adjust(1, 1)
    return kbb.as_markup()


@router.message(Command(commands.START))
async def start_handler(msg: Message, state: FSMContext, command: CommandObject):
    if not command.args:
        await msg.answer(strings.LOG_IN__NO_ACCESS_KEY)
        return
    user_id = msg.from_user.id
    try:
        log_in_data = await service.log_in(user_id, key=command.args)
        account = await service.get_account_by_id(log_in_data.token)
        state_data = await state.get_data()
        start_session_msg_id = state_data.get(START_SESSION_MSG_ID, None)
        await state.set_data({TOKEN: log_in_data.token, START_SESSION_MSG_ID: msg.message_id})

        async def delete_msg(chat_id: int, msg_id: int):
            try:
                await msg.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except TelegramBadRequest as _:
                pass

        if start_session_msg_id:
            wait_msg = await msg.answer(strings.CLEAR_PREVIOUS_SESSION)
            await state.set_state(MainStates.CLEAR_PREVIOUS_SESSION)
            all_msg_ids = list(range(start_session_msg_id, msg.message_id))[::-1]
            for i in range(0, len(all_msg_ids), 5):
                tasks = [delete_msg(msg.chat.id, i) for i in all_msg_ids[i: i + 6]]
                await asyncio.gather(*tasks)
            await wait_msg.delete()
        await msg.answer(strings.LOG_IN__SUCCESS.format(first_name=account.first_name))
        await reset_state(state)
        if log_in_data.is_first:
            text = strings.LOG_IN__SUCCESS__FIRST.format(first_name=account.first_name,
                                                         access_key=log_in_data.access_key)
            keyboard = get_log_in_data_keyboard(account.first_name, access_key=log_in_data.access_key, has_log_in=False)
            await msg.answer(text, reply_markup=keyboard)
        await help_handler(msg, state)
    except KeyNotFoundError:
        await msg.answer(strings.LOG_IN__ACCOUNT_NOT_FOUND)


@router.callback_query(LogInDataCD.filter())
async def log_in_data_callback(callback: CallbackQuery):
    data = LogInDataCD.unpack(callback.data)
    if data.action == data.Action.PIN:
        text = strings.LOG_IN__DATA__PINED.format(first_name=data.first_name, access_key=data.access_key)
        keyboard = get_log_in_data_keyboard(first_name=data.first_name, access_key=data.access_key, has_pin=False)
        await callback.message.edit_text(text=text, reply_markup=keyboard)
        await callback.message.pin(disable_notification=True)
    await callback.answer()


@router.message(RoleCreateStates(), Command(commands.CANCEL))
@router.message(RoleRenameStates(), Command(commands.CANCEL))
@router.message(EmployeeEditEmailStates(), Command(commands.CANCEL))
@router.message(TrainingEditNameStates(), Command(commands.CANCEL))
@router.message(EmployeeEditFullNameStates(), Command(commands.CANCEL))
@router.message(EmployeeCreateStates(), Command(commands.CANCEL))
@router.message(TrainingCreateStates(), Command(commands.CANCEL))
@router.message(LevelCreateStates(), Command(commands.CANCEL))
async def cancel_handler(msg: Message, state: FSMContext):
    await reset_state(state)
    await msg.answer(strings.ACTION_CANCELED)
