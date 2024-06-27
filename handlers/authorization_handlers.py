import asyncio
from typing import Optional

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
from src.strings import eschtml
from data.asvttk_service import asvttk_service as service

router = Router()

TAG_LOG_OUT_WARNING = "lo_warn"


class FirstLogInWarningCD(CallbackData, prefix='f_li_warn'):
    first_name: str
    access_key: str
    action: int

    class Action:
        READ_IT = 0


def get_first_log_in_warning_keyboard(first_name: str, access_key: str):
    kbb = InlineKeyboardBuilder()
    adjust = []
    btn_read_it_data = FirstLogInWarningCD(first_name=first_name, access_key=access_key,
                                           action=FirstLogInWarningCD.Action.READ_IT)
    kbb.add(InlineKeyboardButton(text=strings.BTN_READ_IT, callback_data=btn_read_it_data.pack()))
    adjust += [1]
    kbb.adjust(*adjust)
    return kbb.as_markup()


@router.callback_query(FirstLogInWarningCD.filter())
async def first_log_in_data_callback(callback: CallbackQuery, state: FSMContext):
    data = FirstLogInWarningCD.unpack(callback.data)
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


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_LOG_OUT_WARNING))
async def log_out_warning_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    log_in_access_key = data.args
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            if log_in_access_key:
                await service.check_exist_of_access_key(log_in_access_key)
            await delete_msg(callback.bot, callback.message.chat.id, callback.message.message_id)
            if log_in_access_key:
                await log_in(callback.message, callback.from_user.id, state, access_key=log_in_access_key)
            else:
                await log_out(callback.message, state)
        else:
            await delete_msg(callback.bot, callback.message.chat.id, callback.message.message_id)
    except KeyNotFoundError:
        await callback.message.edit_text(strings.LOG_IN__ACCOUNT_NOT_FOUND, reply_markup=None)
        await asyncio.sleep(2)
        await delete_msg(callback.message.bot, callback.message.chat.id, callback.message.message_id)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


async def show_log_out_warning(token: str, msg: Message, warning_text: str, new_access_key: Optional[str] = None):
    await show_confirmation(token, msg, item_id=0, text=warning_text,
                            tag=TAG_LOG_OUT_WARNING, args=new_access_key, simple=True)


async def log_in(msg: Message, user_id: int, state: FSMContext, access_key: str):
    log_in_data = await service.log_in(user_id, key=access_key)
    account = await service.get_account_by_id(log_in_data.token)
    state_data = await state.get_data()
    asmsgs = state_data.get(ADDITIONAL_SESSION_MSG_IDS, [])
    for i in asmsgs:
        await delete_msg(msg.bot, msg.chat.id, i)
    await log_out(msg, state, new_token=log_in_data.token)
    if log_in_data.account_type != AccountType.STUDENT:
        await msg.answer(strings.LOG_IN__SUCCESS.format(first_name=eschtml(account.first_name)))
    if log_in_data.is_first and account.type != AccountType.STUDENT:
        text = strings.LOG_IN__SUCCESS__FIRST
        keyboard = get_first_log_in_warning_keyboard(account.first_name, access_key=log_in_data.access_key)
        await msg.answer(text, reply_markup=keyboard)
    elif account.type == AccountType.STUDENT:
        await student_handlers.show_start(log_in_data.token, msg, state)
    else:
        await help_handler(msg, state)
