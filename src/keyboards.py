from aiogram.types import SwitchInlineQueryChosenChat, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.models import AccountType
from src import strings
from src.utils import get_access_key_link


def invite_keyboard(account_type: AccountType, access_key: str):
    kbb = InlineKeyboardBuilder()
    if account_type == AccountType.EMPLOYEE:
        text = strings.EMPLOYEE_INVITE_LETTER.format(invite_link=get_access_key_link(access_key))
    elif account_type == AccountType.ADMIN:
        text = strings.ADMIN_INVITE_LETTER.format(invite_link=get_access_key_link(access_key))
    elif account_type == AccountType.STUDENT:
        text = strings.STUDENT_INVITE_LETTER.format(invite_link=get_access_key_link(access_key))
    else:
        raise TypeError
    query = SwitchInlineQueryChosenChat(query=text, allow_user_chats=True)
    kbb.row(InlineKeyboardButton(text=strings.BTN_INVITE, switch_inline_query_chosen_chat=query), width=1)
    return kbb.as_markup()
