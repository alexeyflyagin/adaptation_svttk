import asyncio

from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.exceptions import KeyNotFoundError, TokenNotValidError, UnknownError
from data.asvttk_service.models import AccountType
from handlers import student_handlers
from handlers.handlers_confirmation import ConfirmationCD, show_confirmation
from handlers.handlers_utils import delete_msg, log_out, get_token, ADDITIONAL_SESSION_MSG_IDS, \
    token_not_valid_error_for_callback, unknown_error_for_callback
from handlers.last_handlers import help_handler, show_help
from src import strings
from src.utils import get_access_key_link
from data.asvttk_service import asvttk_service as service

router = Router()

TAG_LOG_IN_WARNING = "log_in_warning"


class LogInDataCD(CallbackData, prefix='log_in_data'):
    first_name: str
    access_key: str
    action: int

    class Action:
        READ_IT = 0


def get_log_in_data_keyboard(first_name: str, access_key: str, has_read_it: bool = True, has_log_in: bool = True):
    kbb = InlineKeyboardBuilder()
    if has_read_it:
        btn_read_it_data = LogInDataCD(first_name=first_name, access_key=access_key, action=LogInDataCD.Action.READ_IT)
        kbb.add(InlineKeyboardButton(text=strings.BTN_READ_IT, callback_data=btn_read_it_data.pack()))
    if has_log_in:
        url = get_access_key_link(access_key=access_key)
        kbb.add(InlineKeyboardButton(text=strings.BTN_LOG_IN, url=url))
    kbb.adjust(1, 1)
    return kbb.as_markup()


@router.callback_query(LogInDataCD.filter())
async def log_in_data_callback(callback: CallbackQuery, state: FSMContext):
    data = LogInDataCD.unpack(callback.data)
    token = await get_token(state)
    try:
        await service.token_validate(token)
        if data.action == data.Action.READ_IT:
            await show_help(token, state, callback.message, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_LOG_IN_WARNING))
async def log_in_warning_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    access_key = data.args
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            await service.check_exist_of_access_key(access_key)
            await log_in(callback.message, callback.from_user.id, state, access_key=access_key)
        await delete_msg(callback.bot, callback.message.chat.id, callback.message.message_id)
    except KeyNotFoundError:
        await callback.message.edit_text(strings.LOG_IN__ACCOUNT_NOT_FOUND, reply_markup=None)
        await asyncio.sleep(2)
        await delete_msg(callback.message.bot, callback.message.chat.id, callback.message.message_id)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


async def show_warning(msg: Message, access_key: str, warning_text: str):
    await show_confirmation("", msg, item_id=0, text=warning_text,
                            tag=TAG_LOG_IN_WARNING, args=access_key, simple=True)


async def log_in(msg: Message, user_id: int, state: FSMContext, access_key: str):
    log_in_data = await service.log_in(user_id, key=access_key)
    account = await service.get_account_by_id(log_in_data.token)
    state_data = await state.get_data()
    asmsgs = state_data.get(ADDITIONAL_SESSION_MSG_IDS, [])
    for i in asmsgs:
        await delete_msg(msg.bot, msg.chat.id, i)
    await log_out(msg, state, new_token=log_in_data.token)
    if log_in_data.account_type != AccountType.STUDENT:
        await msg.answer(strings.LOG_IN__SUCCESS.format(first_name=account.first_name))
    if log_in_data.is_first and account.type != AccountType.STUDENT:
        text = strings.LOG_IN__SUCCESS__FIRST
        keyboard = get_log_in_data_keyboard(account.first_name, access_key=log_in_data.access_key, has_log_in=False)
        await msg.answer(text, reply_markup=keyboard)
    elif account.type == AccountType.STUDENT:
        await student_handlers.show_start(log_in_data.token, msg, state)
    else:
        await help_handler(msg, state)

