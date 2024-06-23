import asyncio
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.exceptions import TokenNotValidError, AccessError
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.models import AccountType
from data.asvttk_service.types import AccountData, EmployeeData
from handlers.authorization_handlers import get_log_in_data_keyboard
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, delete_msg
from src import commands, strings
from src.states import MainStates
from src.strings import field, code, italic
from src.utils import get_account_type_str, show

router = Router()

TAG_LOG_IN_DATA_WARNING = "log_in_data_warning"


class MyAccountCD(CallbackData, prefix="my_account"):
    token: str
    action: int

    class Action:
        LOG_IN_DATA = 1
        LOG_IN_DATA__READ_IT = 2
        LOG_OUT = 3


def log_in_data_instruction_keyboard(token: str) -> InlineKeyboardMarkup:
    kbb = InlineKeyboardBuilder()
    btn_read_it_data = MyAccountCD(token=token, action=MyAccountCD.Action.LOG_IN_DATA__READ_IT)
    kbb.add(InlineKeyboardButton(text=strings.BTN_READ_IT, callback_data=btn_read_it_data.pack()))
    return kbb.as_markup()


def my_account_keyboard(token: str) -> InlineKeyboardMarkup:
    kbb = InlineKeyboardBuilder()
    btn_access_key_data = MyAccountCD(token=token, action=MyAccountCD.Action.LOG_IN_DATA)
    kbb.add(InlineKeyboardButton(text=strings.BTN_ACCESS_KEY, callback_data=btn_access_key_data.pack()))
    return kbb.as_markup()


@router.message(MainStates.ADMIN, Command(commands.MYACCOUNT))
@router.message(MainStates.EMPLOYEE, Command(commands.MYACCOUNT))
async def my_account_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        await show_my_account(token, msg)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(MyAccountCD.filter())
async def my_account_callback(callback: CallbackQuery, state: FSMContext):
    data = MyAccountCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.LOG_IN_DATA:
            keyboard = log_in_data_instruction_keyboard(data.token)
            await callback.message.edit_text(text=strings.LOG_IN_DATA__INSTRUCTION, reply_markup=keyboard)
            await callback.answer()
        elif data.action == data.Action.LOG_IN_DATA__READ_IT:
            await show_my_account(data.token, callback.message, is_answer=False)
            await callback.answer()
            await show_log_in_data(data.token, callback.message)

    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)


async def show_my_account(token: str, msg: Message, edited_msg_id: Optional[int] = None, is_answer: bool = True):
    account: AccountData | EmployeeData
    account = await service.get_account_by_token(token)
    keyboard = my_account_keyboard(token)
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
    await show(msg, text, is_answer, edited_msg_id, keyboard=keyboard)


async def show_log_in_data(token: str, msg: Message):
    log_in_data = await service.get_log_in_data_by_token(token)
    account = await service.get_account_by_token(token)
    keyboard = get_log_in_data_keyboard(account.first_name, log_in_data.access_key, has_read_it=False)
    text = strings.LOG_IN__DATA.format(first_name=account.first_name, access_key=log_in_data.access_key)
    bot_msg = await msg.answer(text, reply_markup=keyboard)
    await asyncio.sleep(60)
    await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
