import dataclasses
import math
import random
from typing import Optional, Any

from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src import strings


class ListCD(CallbackData, prefix="list"):
    token: str
    tag: str
    action: str
    selected_item_id: Optional[int] = None

    class Action:
        NEXT_PAGE = "next_page"
        PREVIOUS_PAGE = "previous_page"
        COUNTER = "counter"
        ADD = "add"
        SELECT = "select"


@dataclasses.dataclass
class ListItem:
    name: str
    item_id: int


def __list_keyboard(token: str, tag: str, page_index: int, page_count: int, page_items: list[ListItem],
                    add_btn_text: Optional[str],
                    has_pages: bool):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if has_pages:
        btn_previous_data = ListCD(token=token, page_index=page_index, page_count=page_count, tag=tag,
                                   action=ListCD.Action.PREVIOUS_PAGE)
        btn_counter_data = ListCD(token=token, page_index=page_index, page_count=page_count, tag=tag,
                                  action=ListCD.Action.COUNTER)
        btn_next_data = ListCD(token=token, page_index=page_index, page_count=page_count, tag=tag,
                               action=ListCD.Action.NEXT_PAGE)
        btn_previous = InlineKeyboardButton(text="«", callback_data=btn_previous_data.pack())
        btn_counter = InlineKeyboardButton(text=f"{page_index + 1} / {page_count}",
                                           callback_data=btn_counter_data.pack())
        btn_next = InlineKeyboardButton(text="»", callback_data=btn_next_data.pack())
        kbb.row(btn_previous, btn_counter, btn_next, width=3)
        adjust.append(3)
    for item in page_items:
        btn_select_item_data = ListCD(token=token, page_index=page_index, page_count=page_count, tag=tag,
                                      action=ListCD.Action.SELECT,
                                      selected_item_id=item.item_id)
        kbb.add(InlineKeyboardButton(text=item.name, callback_data=btn_select_item_data.pack()))
    if page_items:
        adjust.append(len(page_items))
    if add_btn_text:
        btn_add_data = ListCD(token=token, page_index=page_index, page_count=page_count, tag=tag,
                              action=ListCD.Action.ADD)
        kbb.row(InlineKeyboardButton(text=add_btn_text, callback_data=btn_add_data.pack()), width=1)
        adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def list_keyboard(token: str, tag: str, pages: list[list[ListItem]], has_pages: bool = True, page_index: int = 0,
                  add_btn_text: Optional[str] = strings.BTN_ADD) -> InlineKeyboardMarkup:
    if len(pages) <= 1:
        has_pages = False
    return __list_keyboard(token, tag, page_index=page_index, page_count=len(pages), page_items=pages[page_index],
                           add_btn_text=add_btn_text, has_pages=has_pages)


def get_pages(items: list[ListItem], page_size: int = 5) -> list[list[ListItem]]:
    page_count = math.ceil(len(items) / page_size)
    if page_count == 0:
        return [[]]
    return [items[i * page_size:i * page_size + page_size] for i in range(page_count)]


def get_items_by_page(items: list[Any], pages: list[list[ListItem]], page_index: int) -> list[Any]:
    pages = pages[:page_index + 1]
    t = sum([len(i) for i in pages[:-1]])
    return items[t:t + len(pages[-1])]
