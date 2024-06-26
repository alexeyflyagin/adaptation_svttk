import random
from typing import Any, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src import strings


class ConfirmationCD(CallbackData, prefix="confirmation"):
    token: str
    tag: str
    is_agree: bool
    item_id: Optional[int]
    args: Optional[Any] = None
    arg1: Optional[Any] = None


def confirmation_keyboard(token: str, tag: str, item_id: Optional[int], args: Optional[Any] = None,
                          arg1: Optional[Any] = None):
    kbb = InlineKeyboardBuilder()
    kbb.adjust(1)
    btn_yes_data = ConfirmationCD(token=token, tag=tag, is_agree=True, args=args, arg1=arg1, item_id=item_id).pack()
    btn_no_data = ConfirmationCD(token=token, tag=tag, is_agree=False, args=args, arg1=arg1, item_id=item_id).pack()
    btn_yes = InlineKeyboardButton(text=strings.BTN_DELETE_YES, callback_data=btn_yes_data)
    btn_no = InlineKeyboardButton(text=strings.BTN_DELETE_NO, callback_data=btn_no_data)
    btn_no_1 = InlineKeyboardButton(text=strings.BTN_DELETE_NO_1, callback_data=btn_no_data)
    buttons = [btn_yes, btn_no, btn_no_1]
    random.shuffle(buttons)
    kbb.add(*buttons)
    kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE_BACK, callback_data=btn_no_data))
    kbb.adjust(1)
    return kbb.as_markup()


def simple_confirmation_keyboard(token: str, tag: str, item_id: Optional[int] = None, args: Optional[Any] = None,
                                 arg1: Optional[Any] = None):
    kbb = InlineKeyboardBuilder()
    btn_yes_data = ConfirmationCD(token=token, tag=tag, is_agree=True, args=args, arg1=arg1, item_id=item_id).pack()
    btn_no_data = ConfirmationCD(token=token, tag=tag, is_agree=False, args=args, arg1=arg1, item_id=item_id).pack()
    buttons = [InlineKeyboardButton(text=strings.BTN_DELETE_NO, callback_data=btn_no_data),
               InlineKeyboardButton(text=strings.BTN_DELETE_YES, callback_data=btn_yes_data)]
    random.shuffle(buttons)
    kbb.add(*buttons)
    kbb.adjust(2)
    return kbb.as_markup()


async def show_confirmation(token: str, msg: Message, item_id: Optional[int], text: str, tag: str,
                            is_answer: bool = True, args: Optional[Any] = None, arg1: Optional[Any] = None,
                            simple: bool = False):
    keyboard = confirmation_keyboard(token, tag, item_id=item_id, args=args, arg1=arg1)
    if simple:
        keyboard = simple_confirmation_keyboard(token, tag, item_id, args, arg1)
    if is_answer:
        await msg.answer(text, reply_markup=keyboard)
    else:
        await msg.edit_text(text, reply_markup=keyboard)
