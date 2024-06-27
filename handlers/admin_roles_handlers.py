from src.strings import eschtml, item_id
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import RoleNotUniqueNameError, NotFoundError, TokenNotValidError, UnknownError, \
    AccessError, TrainingNotFoundError
from handlers.handlers_confirmation import show_confirmation, ConfirmationCD
from handlers.handlers_list import ListItem, list_keyboard, ListCD, get_safe_page_index, get_pages
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state, \
    unknown_error_for_callback, set_updated_msg, set_updated_item, access_error_for_callback, unknown_error, \
    access_error, get_updated_msg, get_updated_item
from handlers.value_validators import valid_content_type_msg, valid_role_name, ValueNotValidError
from src import commands, strings
from src.states import MainStates, RoleCreateStates, RoleRenameStates
from src.strings import code, field
from src.time_utils import get_date_str, DateFormat
from src.utils import show, ellipsis_text, get_full_name_by_account

router = Router()

TAG_DELETE_ROLE = "r_del"
TAG_ROLES = "r"
TAG_ROLE_TRAININGS = "r_t"
TAG_ROLE_ADD_TRAININGS = "r_a_t"


class RoleCD(CallbackData, prefix="role"):
    token: str
    role_id: Optional[int] = None
    action: int

    class Action:
        BACK = 0
        DELETE = 1
        RENAME = 2
        TRAININGS = 3


def role_keyboard(token: str, role_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if role_id:
        btn_trainings_data = RoleCD(token=token, action=RoleCD.Action.TRAININGS, role_id=role_id)
        btn_delete_data = RoleCD(token=token, action=RoleCD.Action.DELETE, role_id=role_id)
        btn_rename_data = RoleCD(token=token, action=RoleCD.Action.RENAME, role_id=role_id)
        kbb.add(InlineKeyboardButton(text=strings.BTN_TRAININGS, callback_data=btn_trainings_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_RENAME, callback_data=btn_rename_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [2, 1]
    btn_back_data = RoleCD(token=token, action=RoleCD.Action.BACK).pack()
    kbb.add(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data))
    adjust += [1]
    kbb.adjust(*adjust)
    return kbb.as_markup()


@router.callback_query(ListCD.filter(F.tag == TAG_ROLES))
async def roles_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.ADD:
            await state.set_state(RoleCreateStates.NAME)
            await set_updated_msg(state, callback.message.message_id)
            await callback.message.answer(strings.CREATE_ROLE__ENTER_NAME)
        elif data.action == data.Action.SELECT:
            await show_role(data.token, data.selected_item_id, callback.message, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(RoleCD.filter())
async def role_callback(callback: CallbackQuery, state: FSMContext):
    data = RoleCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_roles(data.token, callback.message, is_answer=False)
        else:
            role = await service.get_role_by_id(data.token, data.role_id)
            if data.action == data.Action.DELETE:
                text = strings.ROLE_DELETE.format(role_name=eschtml(role.name))
                await show_confirmation(data.token, callback.message, item_id=data.role_id, text=text,
                                        tag=TAG_DELETE_ROLE, is_answer=False)
            elif data.action == data.Action.RENAME:
                await state.set_state(RoleRenameStates.RENAME)
                await set_updated_item(state, role.id)
                await set_updated_msg(state, callback.message.message_id)
                await callback.message.answer(strings.RENAME_ROLE__ENTER_NAME.format(role_name=eschtml(role.name)))
            elif data.action == data.Action.TRAININGS:
                await show_edit_trainings(data.token, data.role_id, callback.message, is_answer=False)
        await callback.answer()
    except NotFoundError:
        await show_role(data.token, data.role_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
        await show_role(data.token, data.role_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)
        await show_role(data.token, data.role_id, callback.message, is_answer=False)


@router.callback_query(ListCD.filter(F.tag == TAG_ROLE_TRAININGS))
async def edit_trainings_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    role_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_role(data.token, role_id, callback.message, is_answer=False)
        elif data.action == data.Action.SELECT:
            training = await service.get_training_by_id(data.token, data.selected_item_id)
            await service.remove_training_from_role(data.token, role_id=role_id, training_id=training.id)
            await callback.answer(strings.ROLE__TRAININGS__REMOVED.format(training_name=ellipsis_text(training.name)))
            await show_edit_trainings(data.token, role_id, callback.message, is_answer=False)
        elif data.action == data.Action.ADD:
            await show_add_trainings(data.token, role_id, callback.message, is_answer=False)
        elif data.action == data.Action.NEXT_PAGE:
            await show_edit_trainings(data.token, role_id, callback.message, page_index=data.page_index + 1,
                                      is_answer=False)
        elif data.action == data.Action.PREVIOUS_PAGE:
            await show_edit_trainings(data.token, role_id, callback.message, page_index=data.page_index - 1,
                                      is_answer=False)
        await callback.answer()
    except NotFoundError:
        await show_edit_trainings(data.token, role_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
        await show_edit_trainings(data.token, role_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)
        await show_edit_trainings(data.token, role_id, callback.message, is_answer=False)


@router.callback_query(ListCD.filter(F.tag == TAG_ROLE_ADD_TRAININGS))
async def add_trainings_to_role_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    role_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.SELECT:
            training = await service.get_training_by_id(data.token, training_id=data.selected_item_id)
            await service.add_training_to_role(data.token, role_id=role_id, training_id=training.id)
            await callback.answer(strings.ROLE__TRAININGS__ADDED.format(training_name=ellipsis_text(training.name)))
            await show_edit_trainings(data.token, role_id, callback.message, is_answer=False)
        elif data.action == data.Action.BACK:
            await show_edit_trainings(data.token, role_id, callback.message, is_answer=False)
        elif data.action == data.Action.NEXT_PAGE:
            await show_add_trainings(data.token, role_id, callback.message, page_index=data.page_index + 1,
                                     is_answer=False)
        elif data.action == data.Action.PREVIOUS_PAGE:
            await show_add_trainings(data.token, role_id, callback.message, page_index=data.page_index - 1,
                                     is_answer=False)
        await callback.answer()
    except (NotFoundError, TrainingNotFoundError):
        await show_add_trainings(data.token, role_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
        await show_add_trainings(data.token, role_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)
        await show_add_trainings(data.token, role_id, callback.message, is_answer=False)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_DELETE_ROLE))
async def delete_role_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    try:
        if data.is_agree:
            role = await service.get_role_by_id(data.token, data.item_id)
            await service.delete_role(data.token, data.item_id)
            await callback.answer(text=strings.ROLE_DELETED.format(role_name=eschtml(role.name)))
            await show_roles(data.token, callback.message, is_answer=False)
        else:
            await show_role(data.token, data.item_id, callback.message, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await show_role(data.token, data.item_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
        await show_role(data.token, data.item_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)
        await show_role(data.token, data.item_id, callback.message, is_answer=False)


@router.message(RoleCreateStates.NAME)
async def create_role_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        valid_role_name(msg.text)
        role = await service.create_role(token, name=msg.text)
        await msg.answer(strings.CREATE_ROLE__SUCCESS.format(role_name=eschtml(role.name)))
        updated_msg_id, args = await get_updated_msg(state)
        await show_roles(token, msg, edited_msg_id=updated_msg_id)
        await reset_state(state)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except RoleNotUniqueNameError:
        await msg.answer(strings.error_value(strings.VALUE_ERROR__ROLE__UNIQUE_NAME_ERROR))
    except AccessError:
        await access_error(msg, state)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)
        await reset_state(state)


@router.message(RoleRenameStates.RENAME)
async def rename_role_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        valid_role_name(msg.text)
        role_id, args = await get_updated_item(state)
        await service.update_role(token, role_id=role_id, name=msg.text)
        await msg.answer(strings.ROLE__RENAME__SUCCESS)
        updated_msg_id, args = await get_updated_msg(state)
        await show_role(token, role_id, msg, edited_msg_id=updated_msg_id)
        await reset_state(state)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except RoleNotUniqueNameError:
        await msg.answer(strings.error_value(strings.VALUE_ERROR__ROLE__UNIQUE_NAME_ERROR))
    except NotFoundError:
        await msg.answer(strings.ROLE__NOT_FOUND)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)
        await reset_state(state)


@router.message(MainStates.ADMIN, Command(commands.ROLES))
async def roles_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        await show_roles(token, msg, is_answer=True)
    except AccessError:
        await access_error(msg, state, canceled=False)
    except (TokenNotValidError, NotFoundError):
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state, canceled=False)


async def show_roles(token: str, msg: Message, edited_msg_id: Optional[int] = None, is_answer: bool = True):
    try:
        roles = await service.get_all_roles(token)
        text = strings.ROLES if roles else strings.ROLES__EMPTY
        list_items = [ListItem(i.name, i.id, i) for i in roles]
        keyboard = list_keyboard(token, TAG_ROLES, pages=[list_items], max_btn_in_row=2)
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        await msg.answer(strings.ERROR__ACCESS)
    except NotFoundError:
        raise TokenNotValidError()


async def show_role(token: str, role_id: int, msg: Message = None, edited_msg_id: Optional[int] = None,
                    is_answer: bool = True):
    keyboard = role_keyboard(token)
    text = strings.ROLE__NOT_FOUND
    try:
        role = await service.get_role_by_id(token, role_id)
        employees_list = field(" | ".join([code(eschtml(get_full_name_by_account(i))) for i in role.accounts]))
        trainings_list = field(" | ".join([code(eschtml(ellipsis_text(i.name))) for i in role.trainings]))
        date_create = get_date_str(role.date_create, DateFormat.FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE)
        text = strings.ROLE.format(role_name=eschtml(role.name), date_create=date_create, employees_list=employees_list,
                                   trainings_list=trainings_list, item_id=item_id(role.id))
        keyboard = role_keyboard(token, role_id=role_id)
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        text = strings.ERROR__ACCESS
        await show(msg, text, keyboard=keyboard, is_answer=False)
    except NotFoundError:
        await show(msg, text, keyboard=keyboard, is_answer=False)


async def show_edit_trainings(token: str, role_id: int, msg: Message, page_index: int = 0, is_answer: bool = True):
    try:
        role = await service.get_role_by_id(token, role_id)
        trainings = role.trainings
        list_items = [ListItem(ellipsis_text(i.name), i.id) for i in trainings]
        pages = get_pages(list_items, 5)
        page_index = get_safe_page_index(page_index, len(pages))
        keyboard = list_keyboard(token, tag=TAG_ROLE_TRAININGS, pages=pages, max_btn_in_row=1,
                                 page_index=page_index, arg=role_id, back_btn_text=strings.BTN_BACK, up=True)
        text = strings.ROLE__TRAININGS.format(role_name=eschtml(role.name))
        await show(msg, text, is_answer, keyboard=keyboard)
    except AccessError:
        await show_role(token, role_id, msg)
    except NotFoundError:
        await show_role(token, role_id, msg)


async def show_add_trainings(token: str, role_id: int, msg: Message, page_index: int = 0, is_answer: bool = True):
    try:
        text = strings.ROLE__ALL_TRAININGS__FULL
        all_trainings = await service.get_all_trainings(token)
        role = await service.get_role_by_id(token, role_id)
        exist_trainings_ids = [i.id for i in role.trainings]
        trainings = [i for i in all_trainings if i.id not in exist_trainings_ids]
        list_items = [ListItem(ellipsis_text(i.name), i.id) for i in trainings]
        pages = get_pages(list_items, 5)
        page_index = get_safe_page_index(page_index, len(pages))
        keyboard = list_keyboard(token, tag=TAG_ROLE_ADD_TRAININGS, pages=pages, page_index=page_index,
                                 max_btn_in_row=1, arg=role_id, add_btn_text=None, back_btn_text=strings.BTN_BACK,
                                 up=True)
        if trainings:
            text = strings.ROLE__ALL_TRAININGS
        elif not all_trainings:
            text = strings.ROLE__ALL_TRAININGS__NOT_FOUND
        await show(msg, text, is_answer, keyboard=keyboard)
    except AccessError:
        await show_role(token, role_id, msg)
    except NotFoundError:
        await show_role(token, role_id, msg)
