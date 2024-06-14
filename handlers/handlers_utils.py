from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from custom_storage import TOKEN
from data.asvttk_service.models import AccountType
from src import strings
from src.states import MainStates
from data.asvttk_service import asvttk_service as service
from src.utils import TEMPORARY_MSGS


async def reset_state(state: FSMContext, msg: Optional[Message] = None, delete_temporary_msgs: bool = True):
    token = await get_token(state)
    state_date = await state.get_data()
    if msg and delete_temporary_msgs:
        msgs = state_date.get(TEMPORARY_MSGS, None)
        if msgs and len(msgs) < 20:
            msgs = msgs[::-1]
            try:
                for i in msgs:
                    await msg.bot.delete_message(msg.chat.id, i)
            except TelegramBadRequest:
                pass
    await state.set_data({TOKEN: token})
    if token:
        account = await service.get_account_by_id(token)
        if account.type == AccountType.ADMIN:
            await state.set_state(MainStates.ADMIN)
        elif account.type == AccountType.EMPLOYEE:
            await state.set_state(MainStates.EMPLOYEE)
        elif account.type == AccountType.STUDENT:
            await state.set_state(MainStates.STUDENT)
    else:
        await state.set_state(None)


async def add_temporary_msg_id(state: FSMContext, msg: Message):
    state_data = await state.get_data()
    temporary_msg_ids = state_data.get(TEMPORARY_MSGS, [])
    await state.update_data({TEMPORARY_MSGS: temporary_msg_ids + [msg.message_id]})


async def get_token(state: FSMContext):
    state_data = await state.get_data()
    state_token = state_data.get(TOKEN, None)
    return state_token


async def token_not_valid_error(msg: Message, state: FSMContext):
    await state.update_data({TOKEN: None})
    await reset_state(state)
    await msg.answer(text=strings.SESSION_ERROR)


async def token_not_valid_error_for_callback(callback: CallbackQuery):
    await callback.answer(strings.SESSION_ERROR)
    await callback.message.edit_reply_markup(inline_message_id=None)
