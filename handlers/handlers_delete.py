import random
from typing import Any, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src import strings


class DeleteItemCD(CallbackData, prefix="delete"):
    token: str
    tag: str
    is_delete: bool
    deleted_item_id: int
    args: Optional[Any] = None


def delete_keyboard(token: str, tag: str, deleted_item_id: int, args: Optional[Any] = None):
    kbb = InlineKeyboardBuilder()
    kbb.adjust(1)
    btn_yes_data = DeleteItemCD(token=token, tag=tag, is_delete=True, args=args, deleted_item_id=deleted_item_id).pack()
    btn_no_data = DeleteItemCD(token=token, tag=tag, is_delete=False, args=args, deleted_item_id=deleted_item_id).pack()
    btn_yes = InlineKeyboardButton(text=strings.BTN_DELETE_YES, callback_data=btn_yes_data)
    btn_no = InlineKeyboardButton(text=strings.BTN_DELETE_NO, callback_data=btn_no_data)
    btn_no_1 = InlineKeyboardButton(text=strings.BTN_DELETE_NO_1, callback_data=btn_no_data)
    buttons = [btn_yes, btn_no, btn_no_1]
    random.shuffle(buttons)
    kbb.add(*buttons)
    kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE_BACK, callback_data=btn_no_data))
    kbb.adjust(1)
    return kbb.as_markup()


async def show_delete(token: str, msg: Message, deleted_item_id: int, text: str, tag: str,
                      is_answer: bool = True, args: Optional[Any] = None):
    keyboard = delete_keyboard(token, tag, deleted_item_id=deleted_item_id, args=args)
    if is_answer:
        await msg.answer(text, reply_markup=keyboard)
    else:
        await msg.edit_text(text, reply_markup=keyboard)
