from datetime import datetime
from typing import Optional, Any

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.exceptions import TokenNotValidError, AccessError, EmptyFieldError, NotFoundError
from data.asvttk_service.types import TrainingData
from handlers.handlers_delete import delete_keyboard, DeleteItemCD, show_delete
from handlers.handlers_list import ListItem, get_pages, get_safe_page_index, list_keyboard, get_items_by_page, ListCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state
from data.asvttk_service import asvttk_service as service
from src import commands, strings
from src.states import MainStates, TrainingCreateStates, TrainingEditNameStates
from src.utils import show, cut_text, get_training_status

router = Router()

TAG_TRAININGS = "trainings"
TAG_CHOOSE_ROLE = "choose_role"
TAG_TRAINING_DELETE = "training_del"


class TrainingCD(CallbackData, prefix="training"):
    token: str
    training_id: Optional[int] = None
    page_index: int
    action: int

    class Action:
        BACK = 0
        DELETE = 1
        EDIT_NAME = 2


def training_keyboard(token: str, page_index: int, training_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if training_id:
        btn_edit_name_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                        action=TrainingCD.Action.EDIT_NAME)
        btn_delete_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                     action=TrainingCD.Action.DELETE)
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_NAME, callback_data=btn_edit_name_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [1, 1]
    btn_back_data = TrainingCD(token=token, page_index=page_index, action=TrainingCD.Action.BACK)
    kbb.add(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


@router.message(MainStates.ADMIN, Command(commands.TRAININGS))
@router.message(MainStates.EMPLOYEE, Command(commands.TRAININGS))
async def trainings_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await show_trainings(token, msg)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(ListCD.filter(F.tag == TAG_TRAININGS))
async def trainings_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        await state.update_data({"updated_msg": None})
        if data.action == data.Action.ADD:
            await state.set_state(TrainingCreateStates.NAME)
            await callback.message.answer(strings.CREATE_TRAINING__NAME)
            await state.update_data({"updated_msg": [callback.message.message_id, data.page_index]})
        elif data.action == data.Action.SELECT:
            await show_training(data.token, data.selected_item_id, callback.message, data.page_index, is_answer=False)
        elif data.action == data.Action.PREVIOUS_PAGE:
            await show_trainings(data.token, callback.message, page_index=data.page_index - 1, is_answer=False)
        elif data.action == data.Action.NEXT_PAGE:
            await show_trainings(data.token, callback.message, page_index=data.page_index + 1, is_answer=False)
        elif data.action == data.Action.COUNTER:
            await show_trainings(data.token, callback.message, page_index=data.page_index, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(TrainingCD.filter())
async def training_callback(callback: CallbackQuery, state: FSMContext):
    data = TrainingCD.unpack(callback.data)
    try:
        await state.update_data({"update_msg": None})
        if data.action == data.Action.BACK:
            await show_trainings(data.token, callback.message, data.page_index, is_answer=False)
        elif data.action == data.Action.DELETE:
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__DELETE.format(training_name=training.name)
            await show_delete(data.token, callback.message, tag=TAG_TRAINING_DELETE, deleted_item_id=data.training_id,
                              args=data.page_index, is_answer=False, text=text)
        elif data.action == data.Action.EDIT_NAME:
            await state.set_state(TrainingEditNameStates.NAME)
            await callback.message.answer(strings.TRAINING__EDIT_NAME)
            await state.update_data({"updated_item_id": data.training_id})
            await state.update_data({"update_msg": [callback.message.message_id, data.page_index]})
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(DeleteItemCD.filter(F.tag == TAG_TRAINING_DELETE))
async def delete_training_callback(callback: CallbackQuery):
    data = DeleteItemCD.unpack(callback.data)
    page_index = int(data.args)
    try:
        if data.is_delete:
            await service.delete_training(data.token, data.deleted_item_id)
            await show_trainings(data.token, callback.message, page_index, is_answer=False)
            await callback.answer(strings.TRAINING__DELETED)
        else:
            await show_training(data.token, data.deleted_item_id, callback.message, page_index, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await show_training(data.token, data.deleted_item_id, callback.message, page_index, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(TrainingCreateStates.NAME)
async def create_training_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.create_training(token, msg.text)
        await msg.answer(strings.CREATE_TRAINING__CREATED)
        await reset_state(state)
        state_data = await state.get_data()
        updated_msg: Optional[Any] = state_data.get("updated_msg", None)
        if updated_msg:
            await show_trainings(token, msg, page_index=updated_msg[1], edited_msg_id=updated_msg[0], is_answer=False)
    except ValueError:
        await state.set_state(TrainingCreateStates.ROLE)
        await state.update_data({"new_training_name": msg.text})
        await show_choose_role(token, msg)
    except EmptyFieldError:
        pass
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(ListCD.filter(F.tag == TAG_CHOOSE_ROLE))
async def create_training_role_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    state_state = await state.get_state()
    if state_state not in TrainingCreateStates.__all_states_names__:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer(strings.ACTION_CANCELED)
        return
    try:
        state_data = await state.get_data()
        name = state_data.get("new_training_name")
        await service.create_training(data.token, name, role_id=data.selected_item_id)
        role = await service.get_role_by_id(data.token, data.selected_item_id)
        await callback.message.edit_text(strings.CREATE_TRAINING__ROLE__SELECTED.format(role_name=role.name))
        await callback.message.answer(strings.CREATE_TRAINING__CREATED)
        await reset_state(state)
        state_data = await state.get_data()
        updated_msg: Optional[Any] = state_data.get("updated_msg", None)
        if updated_msg:
            await show_trainings(data.token, callback.message, page_index=updated_msg[1], edited_msg_id=updated_msg[0],
                                 is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(TrainingEditNameStates.NAME)
async def edit_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.TRAINING__EDIT_NAME__ERROR__INCORRECT_FORMAT)
        return
    try:
        state_data = await state.get_data()
        employee_id = state_data.get("updated_item_id")
        update_msg = state_data.get("update_msg")
        await service.update_name_training(token, employee_id, name=msg.text)
        await msg.answer(strings.TRAINING__EDIT_NAME__SUCCESS)
        if update_msg:
            await show_training(token, employee_id, msg, update_msg[1], update_msg[0], is_answer=False)
        await reset_state(state)
    except NotFoundError:
        await msg.answer(text=strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


async def show_trainings(token: str, msg: Message, page_index: int = 0, edited_msg_id: Optional[int] = None,
                         is_answer: bool = True):
    text = strings.TRAININGS__UNAVAILABLE
    keyboard = None
    try:
        trainings = await service.get_all_trainings(token)
        list_items = [ListItem(str(i + 1), trainings[i].id) for i in range(len(trainings))]
        pages = get_pages(list_items)
        page_index = get_safe_page_index(page_index, len(pages))
        keyboard = list_keyboard(token=token, tag=TAG_TRAININGS, pages=pages, page_index=page_index)
        trainings: list[TrainingData] = get_items_by_page(trainings, pages, page_index)
        items = pages[page_index]
        str_items = []
        for i in range(len(trainings)):
            str_items.append(strings.TRAININGS_ITEM.format(
                index=items[i].name,
                title=cut_text(trainings[i].name),
                status=get_training_status(trainings[i]),
                student_counter=len(trainings[i].students),
            ))
        text = "\n\n".join(str_items)
        if not trainings:
            text = strings.TRAININGS__EMPTY
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_training(token: str, training_id: int, msg: Message, page_index: int = 0,
                        edited_msg_id: Optional[int] = None, is_answer: bool = True):
    text = strings.TRAINING__NOT_FOUND
    keyboard = training_keyboard(token, page_index)
    try:
        training = await service.get_training_by_id(token, training_id)
        keyboard = training_keyboard(token, page_index, training_id)
        text = strings.TRAINING.format(
            name=training.name,
            level_counter=len(training.levels),
            students_counter=len(training.students),
            status=get_training_status(training),
            data_create=datetime.fromtimestamp(training.date_create).strftime(strings.DATE_FORMAT_FULL),
        )
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_choose_role(token: str, msg: Message, edited_msg_id: Optional[int] = None, page_index: int = 0,
                           is_answer: bool = True):
    text = strings.CREATE_TRAINING__ROLE
    all_roles = await service.get_all_roles(token)
    list_items = [ListItem(i.name, i.id) for i in all_roles]
    keyboard = list_keyboard(token, tag=TAG_CHOOSE_ROLE, pages=[list_items], max_btn_in_row=2, arg=page_index,
                             add_btn_text=None)
    await show(msg, text, is_answer, edited_msg_id, keyboard)
