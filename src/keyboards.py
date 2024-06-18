from typing import Optional

from aiogram.types import SwitchInlineQueryChosenChat, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.models import AccountType
from src import strings
from src.utils import get_access_key_link


def invite_keyboard(account_type: AccountType, access_key: str, training_name: Optional[str] = None):
    kbb = InlineKeyboardBuilder()
    if account_type == AccountType.EMPLOYEE:
        text = strings.EMPLOYEE_INVITE_LETTER.format(invite_link=get_access_key_link(access_key))
    elif account_type == AccountType.STUDENT and training_name:
        text = strings.STUDENT_INVITE_LETTER.format(invite_link=get_access_key_link(access_key),
                                                    training_name=training_name)
    else:
        raise TypeError
    query = SwitchInlineQueryChosenChat(query=text, allow_user_chats=True)
    kbb.row(InlineKeyboardButton(text=strings.BTN_INVITE, switch_inline_query_chosen_chat=query), width=1)
    return kbb.as_markup()
