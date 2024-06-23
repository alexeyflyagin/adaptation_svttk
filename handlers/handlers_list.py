import math
from typing import Optional, Any

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src import strings
from src.types import CALLBACK_DATA_SEP


class ListCD(CallbackData, prefix="list", sep=CALLBACK_DATA_SEP):
    token: str
    tag: str
    page_index: int
    action: int
    arg: Any
    arg1: Any
    selected_item_id: Optional[int] = None

    class Action:
        NEXT_PAGE = 0
        PREVIOUS_PAGE = 1
        COUNTER = 2
        ADD = 3
        SELECT = 4
        BACK = 5


class ListItem:
    def __init__(self, name: str, item_id: int, obj: Optional[Any] = None):
        self.name = name
        self.item_id = item_id
        self.obj = obj


def __list_keyboard(token: str, tag: str, page_index: int, page_count: int, page_items: list[ListItem],
                    add_btn_text: Optional[str], has_pages: bool, max_btn_in_row: Optional[int],
                    back_btn_text: Optional[str], arg: Optional[Any] = None, arg1: Optional[Any] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if has_pages:
        btn_previous_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                                   action=ListCD.Action.PREVIOUS_PAGE)
        btn_counter_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                                  action=ListCD.Action.COUNTER)
        btn_next_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                               action=ListCD.Action.NEXT_PAGE)
        btn_previous = InlineKeyboardButton(text="«", callback_data=btn_previous_data.pack())
        btn_counter = InlineKeyboardButton(text=f"{page_index + 1} / {page_count}",
                                           callback_data=btn_counter_data.pack())
        btn_next = InlineKeyboardButton(text="»", callback_data=btn_next_data.pack())
        kbb.row(btn_previous, btn_counter, btn_next, width=3)
        adjust.append(3)
    for item in page_items:
        btn_select_item_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                                      action=ListCD.Action.SELECT, selected_item_id=item.item_id)
        kbb.add(InlineKeyboardButton(text=item.name, callback_data=btn_select_item_data.pack()))
    if page_items and not max_btn_in_row:
        adjust.append(len(page_items))
    elif page_items and max_btn_in_row:
        if max_btn_in_row > len(page_items):
            adjust.append(len(page_items))
        else:
            adjust += [max_btn_in_row] * (len(page_items) // max_btn_in_row)
            if len(page_items) % max_btn_in_row != 0:
                adjust += [len(page_items) % max_btn_in_row]
    if add_btn_text:
        btn_add_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                              action=ListCD.Action.ADD)
        kbb.row(InlineKeyboardButton(text=add_btn_text, callback_data=btn_add_data.pack()))
        adjust.append(1)
    if back_btn_text:
        btn_back_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                               action=ListCD.Action.BACK)
        kbb.row(InlineKeyboardButton(text=back_btn_text, callback_data=btn_back_data.pack()))
        adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def __list_keyboard_up(token: str, tag: str, page_index: int, page_count: int, page_items: list[ListItem],
                       add_btn_text: Optional[str], has_pages: bool, max_btn_in_row: Optional[int],
                       back_btn_text: Optional[str], arg: Optional[Any] = None, arg1: Optional[Any] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    for item in page_items:
        btn_select_item_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                                      action=ListCD.Action.SELECT, selected_item_id=item.item_id)
        kbb.add(InlineKeyboardButton(text=item.name, callback_data=btn_select_item_data.pack()))
    if page_items and not max_btn_in_row:
        adjust.append(len(page_items))
    elif page_items and max_btn_in_row:
        if max_btn_in_row > len(page_items):
            adjust.append(len(page_items))
        else:
            adjust += [max_btn_in_row] * (len(page_items) // max_btn_in_row)
            if len(page_items) % max_btn_in_row != 0:
                adjust += [len(page_items) % max_btn_in_row]
    if has_pages:
        btn_previous_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                                   action=ListCD.Action.PREVIOUS_PAGE)
        btn_counter_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                                  action=ListCD.Action.COUNTER)
        btn_next_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                               action=ListCD.Action.NEXT_PAGE)
        btn_previous = InlineKeyboardButton(text="«", callback_data=btn_previous_data.pack())
        btn_counter = InlineKeyboardButton(text=f"{page_index + 1} / {page_count}",
                                           callback_data=btn_counter_data.pack())
        btn_next = InlineKeyboardButton(text="»", callback_data=btn_next_data.pack())
        kbb.row(btn_previous, btn_counter, btn_next, width=3)
        adjust.append(3)
    if add_btn_text:
        btn_add_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                              action=ListCD.Action.ADD)
        kbb.row(InlineKeyboardButton(text=add_btn_text, callback_data=btn_add_data.pack()))
        adjust.append(1)
    if back_btn_text:
        btn_back_data = ListCD(token=token, page_index=page_index, tag=tag, arg=arg, arg1=arg1,
                               action=ListCD.Action.BACK)
        kbb.row(InlineKeyboardButton(text=back_btn_text, callback_data=btn_back_data.pack()))
        adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def list_keyboard(token: str, tag: str, pages: list[list[ListItem]], has_pages: bool = True, page_index: int = 0,
                  add_btn_text: Optional[str] = strings.BTN_ADD,
                  max_btn_in_row: Optional[int] = None, back_btn_text: Optional[str] = None,
                  arg: Optional[Any] = None, arg1: Optional[Any] = None, up: bool = False) -> InlineKeyboardMarkup:
    if len(pages) <= 1:
        has_pages = False
    if up:
        return __list_keyboard_up(token, tag, page_index=page_index, page_count=len(pages),
                                  page_items=pages[page_index], add_btn_text=add_btn_text, has_pages=has_pages,
                                  max_btn_in_row=max_btn_in_row, back_btn_text=back_btn_text, arg=arg, arg1=arg1)
    return __list_keyboard(token, tag, page_index=page_index, page_count=len(pages), page_items=pages[page_index],
                           add_btn_text=add_btn_text, has_pages=has_pages, max_btn_in_row=max_btn_in_row,
                           back_btn_text=back_btn_text, arg=arg, arg1=arg1)


def get_pages(items: list[ListItem], page_size: int = 5) -> list[list[ListItem]]:
    page_count = math.ceil(len(items) / page_size)
    if page_count == 0:
        return [[]]
    return [items[i * page_size:i * page_size + page_size] for i in range(page_count)]


def get_items_by_page(items: list[Any], pages: list[list[ListItem]], page_index: int) -> list[Any]:
    pages = pages[:page_index + 1]
    t = sum([len(i) for i in pages[:-1]])
    return items[t:t + len(pages[-1])]


def get_safe_page_index(page_index: int, page_count: int) -> int:
    if page_index >= page_count:
        page_index = page_index % page_count
    elif page_index < 0:
        page_index = page_count - abs(page_index) % page_count
    return page_index
