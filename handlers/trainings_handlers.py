from datetime import datetime
from typing import Optional, Any

from aiogram import Router, F
from aiogram.enums import ContentType, PollType
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_album import AlbumMessage

from data.asvttk_service.exceptions import TokenNotValidError, AccessError, EmptyFieldError, NotFoundError, \
    TrainingStateError, TrainingIsActiveError, TrainingIsNotActiveError, InitialsValueError
from data.asvttk_service.models import LevelType, AccountType
from data.asvttk_service.types import TrainingData, StudentData
from handlers.handlers_confirmation import ConfirmationCD, show_confirmation, confirmation_keyboard
from handlers.handlers_list import ListItem, get_pages, get_safe_page_index, list_keyboard, get_items_by_page, ListCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state, \
    send_msg, get_content_type_srt, get_content_text
from data.asvttk_service import asvttk_service as service
from src import commands, strings
from src.keyboards import invite_keyboard
from src.states import MainStates, TrainingCreateStates, TrainingEditNameStates, LevelCreateStates, \
    TrainingStartEditStates, LevelEditStates, StudentCreateState
from src.strings import blockquote
from src.utils import show, cut_text, get_training_status, CONTENT_TYPE__MEDIA_GROUP, UPDATED_MSG, UPDATED_ITEM_ID, \
    get_level_type_from_content_type, is_started_training, get_full_name_by_account, get_initials_from_text, \
    get_access_key_link

router = Router()

TAG_TRAININGS = "trainings"
TAG_STUDENTS = "students"
TAG_CHOOSE_ROLE = "choose_role"
TAG_TRAINING_DELETE = "training_del"
TAG_TRAINING_START = "training_st"
TAG_TRAINING_STOP = "training_en"
TAG_LEVELS = "levels"
TAG_DELETE_LEVEL = "level_del"


class TrainingCD(CallbackData, prefix="training"):
    token: str
    training_id: Optional[int] = None
    page_index: int
    action: int

    class Action:
        BACK = 0
        DELETE = 1
        EDIT_NAME = 2
        LEVELS = 3
        START = 4
        STOP = 5
        STUDENTS = 6


class LevelCD(CallbackData, prefix="level"):
    token: str
    level_id: Optional[int] = None
    training_id: int
    action: int

    class Action:
        BACK = 0
        DELETE = 1
        COUNTER = 2
        NEXT_LEVEL = 3
        PREVIOUS_LEVEL = 4
        EDIT_TITLE = 5
        EDIT = 6


class TrainingStartCD(CallbackData, prefix="training_start"):
    token: str
    training_id: int
    action: int

    class Action:
        BACK = 0
        SHOW = 1
        EDIT = 2


def training_keyboard(token: str, page_index: int, training_id: Optional[int] = None, is_started: bool = False,
                      student_counter: Optional[int] = None, level_counter: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if training_id:
        if is_started:
            btn_stop_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                       action=TrainingCD.Action.STOP)
            kbb.add(InlineKeyboardButton(text=strings.BTN_TRAINING_STOP, callback_data=btn_stop_data.pack()))
        else:
            btn_start_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                        action=TrainingCD.Action.START)
            kbb.add(InlineKeyboardButton(text=strings.BTN_TRAINING_START, callback_data=btn_start_data.pack()))
        adjust += [1]
        btn_students_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                       action=TrainingCD.Action.STUDENTS)
        btn_levels_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                     action=TrainingCD.Action.LEVELS)
        btn_edit_name_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                        action=TrainingCD.Action.EDIT_NAME)
        btn_delete_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                     action=TrainingCD.Action.DELETE)
        kbb.add(InlineKeyboardButton(text=strings.BTN_STUDENTS + f" ({student_counter})",
                                     callback_data=btn_students_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_LEVELS + f" ({level_counter})",
                                     callback_data=btn_levels_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_NAME, callback_data=btn_edit_name_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [2, 1, 1]
    btn_back_data = TrainingCD(token=token, page_index=page_index, action=TrainingCD.Action.BACK)
    kbb.add(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def level_keyboard(token: str, training_id: int, level_id: Optional[int] = None, i: Optional[int] = None,
                   ii: Optional[int] = None, ):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if level_id:
        btn_previous_data = LevelCD(token=token, level_id=level_id, training_id=training_id,
                                    action=LevelCD.Action.PREVIOUS_LEVEL)
        btn_counter_data = LevelCD(token=token, level_id=level_id, training_id=training_id,
                                   action=LevelCD.Action.COUNTER)
        btn_next_data = LevelCD(token=token, level_id=level_id, training_id=training_id,
                                action=LevelCD.Action.NEXT_LEVEL)
        kbb.add(InlineKeyboardButton(text=strings.BTN_PREVIOUS_SYMBOL, callback_data=btn_previous_data.pack()))
        kbb.add(InlineKeyboardButton(text=f"{i} / {ii}", callback_data=btn_counter_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_NEXT_SYMBOL, callback_data=btn_next_data.pack()))
        adjust += [3]
        btn_delete_data = LevelCD(token=token, level_id=level_id, training_id=training_id, action=LevelCD.Action.DELETE)
        btn_edit_title_data = LevelCD(token=token, level_id=level_id, training_id=training_id,
                                      action=LevelCD.Action.EDIT_TITLE)
        btn_edit_data = LevelCD(token=token, level_id=level_id, training_id=training_id, action=LevelCD.Action.EDIT)
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_TITLE, callback_data=btn_edit_title_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_CONTENT, callback_data=btn_edit_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [2, 1]
    btn_back_data = LevelCD(token=token, level_id=level_id, training_id=training_id, action=LevelCD.Action.BACK)
    kbb.add(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def training_start_keyboard(token: str, training_id: int):
    kbb = InlineKeyboardBuilder()
    adjust = []
    btn_show_data = TrainingStartCD(token=token, training_id=training_id, action=TrainingStartCD.Action.SHOW)
    btn_edit_text_data = TrainingStartCD(token=token, training_id=training_id, action=TrainingStartCD.Action.EDIT)
    kbb.add(InlineKeyboardButton(text=strings.BTN_SHOW, callback_data=btn_show_data.pack()))
    kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT, callback_data=btn_edit_text_data.pack()))
    adjust += [1, 1]
    btn_back_data = TrainingStartCD(token=token, training_id=training_id, action=LevelCD.Action.BACK)
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
        await state.update_data({UPDATED_MSG: None})
        if data.action == data.Action.ADD:
            await state.set_state(TrainingCreateStates.NAME)
            await callback.message.answer(strings.CREATE_TRAINING__NAME)
            await state.update_data({UPDATED_MSG: [callback.message.message_id, data.page_index]})
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
        await state.update_data({UPDATED_MSG: None})
        if data.action == data.Action.BACK:
            await show_trainings(data.token, callback.message, data.page_index, is_answer=False)
        elif data.action == data.Action.DELETE:
            await service.training_is_started_check(data.token, data.training_id)
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__DELETE.format(training_name=training.name)
            await show_confirmation(data.token, callback.message, tag=TAG_TRAINING_DELETE, item_id=data.training_id,
                                    args=data.page_index, is_answer=False, text=text)
        elif data.action == data.Action.EDIT_NAME:
            await service.training_is_started_check(data.token, data.training_id)
            await state.set_state(TrainingEditNameStates.NAME)
            await callback.message.answer(strings.TRAINING__EDIT_NAME)
            await state.update_data({UPDATED_ITEM_ID: data.training_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id, data.page_index]})
        elif data.action == data.Action.LEVELS:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
        elif data.action == data.Action.START:
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__START.format(training_name=training.name)
            await show_confirmation(data.token, callback.message, data.training_id, text, tag=TAG_TRAINING_START,
                                    is_answer=False, args=data.page_index)
        elif data.action == data.Action.STOP:
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__STOP.format(training_name=training.name)
            await show_confirmation(data.token, callback.message, data.training_id, text, tag=TAG_TRAINING_STOP,
                                    is_answer=False, args=data.page_index)
        elif data.action == data.Action.STUDENTS:
            await show_students(data.token, callback.message, data.training_id, is_answer=False)
        await callback.answer()
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except NotFoundError:
        await show_training(data.token, data.training_id, callback.message, data.page_index, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(ListCD.filter(F.tag == TAG_STUDENTS))
async def students_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    training_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_training(data.token, training_id, callback.message, is_answer=False)
        elif data.action == data.Action.ADD:
            await service.training_is_not_started_check(data.token, training_id)
            await reset_state(state)
            await callback.message.answer(strings.STUDENTS__ENTER__FULL_NAME)
            await state.set_state(StudentCreateState.FULL_NAME)
            await state.update_data({UPDATED_ITEM_ID: training_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id, data.page_index]})
        await callback.answer()
    except TrainingIsNotActiveError:
        await callback.answer(strings.TRAINING_IS_NOT_STARTED_ERROR)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(StudentCreateState.FULL_NAME)
async def create_student_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        if msg.content_type != ContentType.TEXT:
            raise InitialsValueError()
        state_date = await state.get_data()
        updated_item_id = state_date.get(UPDATED_ITEM_ID, None)
        initials = get_initials_from_text(msg.text, has_none=True)
        acc_data = await service.create_student(token, updated_item_id, initials[1], initials[0], initials[2])
        training = await service.get_training_by_id(token, updated_item_id)
        keyboard = invite_keyboard(AccountType.STUDENT, acc_data.access_key, training.name)
        text = strings.CREATE_STUDENT__SUCCESS.format(access_key=acc_data.access_key,
                                                      access_link=get_access_key_link(acc_data.access_key))
        await msg.answer(text, reply_markup=keyboard)
        updated_msg = state_date.get(UPDATED_MSG, None)
        if updated_msg:
            await show_students(token, msg, updated_item_id, edited_msg_id=updated_msg[0], page_index=updated_msg[1],
                                is_answer=True)
        await reset_state(state)
    except InitialsValueError:
        await msg.answer(strings.CREATE_ACCOUNT__ERROR_FORMAT)
    except TrainingIsNotActiveError:
        await msg.answer(strings.TRAINING_IS_NOT_STARTED_ERROR)
        await reset_state(state)
    except NotFoundError:
        await msg.answer(strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_TRAINING_START))
async def start_training_callback(callback: CallbackQuery):
    data = ConfirmationCD.unpack(callback.data)
    page_index = int(data.args)
    try:
        if data.is_agree:
            await service.start_training(data.token, data.item_id)
            await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
            await callback.answer(strings.TRAINING__STARTED)
        else:
            await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
    except TrainingStateError:
        await callback.answer(strings.TRAINING__STARTED__ERROR__ALREADY_STARTED)
        await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_TRAINING_STOP))
async def stop_training_callback(callback: CallbackQuery):
    data = ConfirmationCD.unpack(callback.data)
    page_index = int(data.args)
    try:
        if data.is_agree:
            await service.stop_training(data.token, data.item_id)
            await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
            await callback.answer(strings.TRAINING__STOPPED)
        else:
            await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
    except TrainingStateError:
        await callback.answer(strings.TRAINING__STARTED__ERROR__NOT_STARTED)
        await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_TRAINING_DELETE))
async def delete_training_callback(callback: CallbackQuery):
    data = ConfirmationCD.unpack(callback.data)
    page_index = int(data.args)
    try:
        if data.is_agree:
            await service.delete_training(data.token, data.item_id)
            await show_trainings(data.token, callback.message, page_index, is_answer=False)
            await callback.answer(strings.TRAINING__DELETED)
        else:
            await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
            await callback.answer()
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except NotFoundError:
        await show_training(data.token, data.item_id, callback.message, page_index, is_answer=False)
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
        updated_msg: Optional[Any] = state_data.get(UPDATED_MSG, None)
        if updated_msg:
            await show_trainings(token, msg, page_index=updated_msg[1], edited_msg_id=updated_msg[0])
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
        updated_msg: Optional[Any] = state_data.get(UPDATED_MSG, None)
        if updated_msg:
            await show_trainings(data.token, callback.message, page_index=updated_msg[1], edited_msg_id=updated_msg[0])
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
        employee_id = state_data.get(UPDATED_ITEM_ID)
        update_msg = state_data.get(UPDATED_MSG)
        await service.update_name_training(token, employee_id, name=msg.text)
        await msg.answer(strings.TRAINING__EDIT_NAME__SUCCESS)
        if update_msg:
            await show_training(token, employee_id, msg, update_msg[1], update_msg[0])
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except NotFoundError:
        await msg.answer(text=strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(ListCD.filter(F.tag == TAG_LEVELS))
async def levels_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    training_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_training(data.token, training_id, callback.message, is_answer=False)
        elif data.action == data.Action.ADD:
            await service.training_is_started_check(data.token, training_id)
            await reset_state(state)
            await callback.message.answer(strings.ENTER__LEVEL__TITLE)
            await state.set_state(LevelCreateStates.TITLE)
            await state.update_data({UPDATED_ITEM_ID: training_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id]})
        elif data.action == data.Action.SELECT and data.selected_item_id != -1:
            await show_about_level(data.token, callback.message, training_id, data.selected_item_id, is_answer=False)
        elif data.action == data.Action.SELECT and data.selected_item_id == -1:
            await show_about_start_level(data.token, callback.message, training_id, is_answer=False)
        await callback.answer()
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(LevelCD.filter())
async def level_callback(callback: CallbackQuery, state: FSMContext):
    data = LevelCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        level = None
        if data.level_id:
            level = await service.get_level_by_id(data.token, data.level_id)
        if data.action == data.Action.BACK:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
        elif data.action == data.Action.NEXT_LEVEL and level.next_level_id:
            await show_about_level(data.token, callback.message, data.training_id, level.next_level_id, is_answer=False)
        elif data.action == data.Action.PREVIOUS_LEVEL and level.previous_level_id:
            await show_about_level(data.token, callback.message, data.training_id, level.previous_level_id,
                                   is_answer=False)
        elif data.action == data.Action.DELETE:
            await service.training_is_started_check(data.token, data.training_id)
            level = await service.get_level_by_id(data.token, data.level_id)
            text = strings.LEVEL__DELETE.format(level_name=cut_text(level.title),
                                                training_name=cut_text(level.training.name))
            await show_confirmation(data.token, callback.message, data.level_id, text, TAG_DELETE_LEVEL,
                                    is_answer=False,
                                    args=data.training_id)
        elif data.action == data.Action.COUNTER:
            await show_level(data.token, callback.message, data.level_id)
        elif data.action == data.Action.EDIT:
            await service.training_is_started_check(data.token, data.training_id)
            await reset_state(state)
            await callback.message.answer(strings.ENTER__LEVEL_CONTENT)
            await state.set_state(LevelEditStates.CONTENT)
            await state.update_data({UPDATED_ITEM_ID: data.level_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id]})
        elif data.action == data.Action.EDIT_TITLE:
            await service.training_is_started_check(data.token, data.training_id)
            await reset_state(state)
            await callback.message.answer(strings.ENTER__LEVEL__TITLE)
            await state.set_state(LevelEditStates.TITLE)
            await state.update_data({UPDATED_ITEM_ID: data.level_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id]})
        await callback.answer()
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except NotFoundError:
        await show_about_level(data.token, callback.message, data.training_id, data.level_id, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_DELETE_LEVEL))
async def delete_level_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    training_id = int(data.args)
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            level = await service.get_level_by_id(data.token, data.item_id)
            await service.delete_level_by_id(data.token, data.item_id)
            await show_levels(data.token, training_id, callback.message, is_answer=False)
            await callback.answer(strings.LEVEL__DELETED.format(level_name=cut_text(level.title)))
        else:
            await show_about_level(data.token, callback.message, training_id, data.item_id, is_answer=False)
            await callback.answer()
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except NotFoundError:
        await show_about_level(data.token, callback.message, training_id, data.level_id, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(LevelEditStates.TITLE)
async def edit_level_title_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.CREATE_LEVEL__TITLE__ERROR__INCORRECT_FORMAT)
        return
    try:
        await service.token_validate(token)
        state_data = await state.get_data()
        level_id = state_data[UPDATED_ITEM_ID]
        await service.update_title_level_by_id(token, level_id, msg.text)
        await msg.answer(strings.EDIT_TITLE_LEVEL__SUCCESS)
        updated_msg = state_data[UPDATED_MSG]
        if updated_msg:
            level = await service.get_level_by_id(token, level_id)
            await show_about_level(token, msg, level.training_id, level_id, edited_msg_id=updated_msg[0])
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except NotFoundError:
        await msg.answer(text=strings.LEVEL__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.message(LevelEditStates.CONTENT)
async def edit_level_content_handler(msg: AlbumMessage, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        if msg.content_type == ContentType.POLL and msg.poll.type == PollType.QUIZ:
            level_type = get_level_type_from_content_type(msg.content_type, PollType.QUIZ)
        else:
            level_type = get_level_type_from_content_type(msg.content_type)
        state_data = await state.get_data()
        level_id = state_data[UPDATED_ITEM_ID]
        messages = msg.messages if msg.content_type == CONTENT_TYPE__MEDIA_GROUP else [msg]
        await service.update_content_level_by_id(token, level_type=level_type, level_id=level_id, messages=messages)
        await msg.answer(strings.EDIT_CONTENT_LEVEL__SUCCESS)
        updated_msg = state_data[UPDATED_MSG]
        if updated_msg:
            level = await service.get_level_by_id(token, level_id)
            await show_about_level(token, msg, level.training_id, level_id, edited_msg_id=updated_msg[0])
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except NotFoundError:
        await msg.answer(text=strings.LEVEL__NOT_FOUND)
        await reset_state(state)
    except TypeError:
        await msg.answer(strings.CREATE_LEVEL__CONTENT__ERROR__INCORRECT_FORMAT)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(TrainingStartCD.filter())
async def start_level_callback(callback: CallbackQuery, state: FSMContext):
    data = TrainingStartCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
        elif data.action == data.Action.SHOW:
            await show_start_level(data.token, callback.message, data.training_id)
        elif data.action == data.Action.EDIT:
            await service.training_is_started_check(data.token, data.training_id)
            await reset_state(state)
            await callback.message.answer(strings.TRAINING__START__EDIT__CONTENT)
            await state.set_state(TrainingStartEditStates.CONTENT)
            await state.update_data({UPDATED_ITEM_ID: data.training_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id]})
        await callback.answer()
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except NotFoundError:
        await show_levels(data.token, data.training_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(TrainingStartEditStates.CONTENT)
async def edit_start_level_handler(msg: AlbumMessage, state: FSMContext):
    token = await get_token(state)
    try:
        if msg.content_type not in [ContentType.PHOTO, ContentType.TEXT]:
            raise TypeError()
        await service.token_validate(token)
        state_data = await state.get_data()
        training_id = state_data[UPDATED_ITEM_ID]
        messages = msg.messages if msg.content_type == CONTENT_TYPE__MEDIA_GROUP else [msg]
        await service.update_start_msg_training(token, training_id=training_id, msg=messages)
        await msg.answer(strings.TRAINING__START__EDIT__CONTENT__SUCCESS)
        updated_msg = state_data[UPDATED_MSG]
        if updated_msg:
            await show_about_start_level(token, msg, training_id, edited_msg_id=updated_msg[0])
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except TypeError:
        await msg.answer(strings.TRAINING__START__EDIT__CONTENT__ERROR__INCORRECT_FORMAT)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


CREATE_LEVEL_TITLE = "create_level_title"


@router.message(LevelCreateStates.TITLE)
async def create_level_title_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.CREATE_LEVEL__TITLE__ERROR__INCORRECT_FORMAT)
        return
    try:
        await service.token_validate(token)
        await state.update_data({CREATE_LEVEL_TITLE: msg.text})
        await state.set_state(LevelCreateStates.CONTENT)
        await msg.answer(strings.ENTER__LEVEL_CONTENT)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.message(LevelCreateStates.CONTENT)
async def create_level_content_handler(msg: AlbumMessage, state: FSMContext):
    token = await get_token(state)

    try:
        await service.token_validate(token)
        if msg.content_type == ContentType.POLL and msg.poll.type == PollType.QUIZ:
            level_type = get_level_type_from_content_type(msg.content_type, PollType.QUIZ)
        else:
            level_type = get_level_type_from_content_type(msg.content_type)
        state_data = await state.get_data()
        title = state_data[CREATE_LEVEL_TITLE]
        training_id = state_data[UPDATED_ITEM_ID]
        messages = msg.messages if msg.content_type == CONTENT_TYPE__MEDIA_GROUP else [msg]
        await service.create_level(token, level_type=level_type, training_id=training_id, title=title,
                                   messages=messages)
        await msg.answer(strings.CREATE_LEVEL__SUCCESS)
        updated_msg = state_data[UPDATED_MSG]
        if updated_msg:
            await show_levels(token, training_id, msg, edited_msg_id=updated_msg[0])
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except TypeError:
        await msg.answer(strings.CREATE_LEVEL__CONTENT__ERROR__INCORRECT_FORMAT)
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
        keyboard = training_keyboard(token, page_index, training_id, is_started=is_started_training(training),
                                     student_counter=len(training.students), level_counter=len(training.levels))
        text = strings.TRAINING.format(
            name=training.name,
            students_counter=len(training.students),
            status=get_training_status(training),
            data_create=datetime.fromtimestamp(training.date_create).strftime(strings.DATE_FORMAT_FULL),
        )
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except NotFoundError:
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


async def show_levels(token: str, training_id: int, msg: Message,
                      edited_msg_id: Optional[int] = None, is_answer: bool = True):
    try:
        training = await service.get_training_by_id(token, training_id)
        levels = await service.get_levels_by_training(token, training_id)
        list_item = [ListItem(strings.TRAININGS__LEVELS__ITEM__TYPE__START_I, item_id=-1)]
        list_item += [ListItem(str(i.order), i.id, i) for i in levels]
        keyboard = list_keyboard(token, tag=TAG_LEVELS, pages=[list_item], max_btn_in_row=5,
                                 back_btn_text=strings.BTN_BACK, arg=training_id)
        items_str = [
            strings.TRAININGS__LEVELS__ITEM__NO_INDEX.format(
                type_icon=strings.TRAININGS__LEVELS__ITEM__TYPE__START_I,
                level_title=cut_text(get_content_text(training.message).strip()),
            )
        ]
        for item in list_item:
            if item.item_id == -1:
                continue
            icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO_I
            if item.obj.type == LevelType.QUIZ:
                icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ_I
            item_str = strings.TRAININGS__LEVELS__ITEM.format(
                type_icon=icon_type_str,
                index=item.name,
                level_title=cut_text(item.obj.title),
            )
            items_str.append(item_str)
        text = strings.TRAINING__LEVELS.format(training_name=cut_text(training.name), items="\n".join(items_str))
        await show(msg, text=text, is_answer=is_answer, edited_msg_id=edited_msg_id, keyboard=keyboard)
    except NotFoundError:
        await show_trainings(token, msg, is_answer=False)


async def show_about_level(token: str, msg: Message, training_id: int, level_id: int,
                           edited_msg_id: Optional[int] = None, is_answer: bool = True):
    text = strings.LEVEL__NOT_FOUND
    keyboard = level_keyboard(token, training_id)
    try:
        level = await service.get_level_by_id(token, level_id)
        levels = await service.get_levels_by_training(token, level.training_id)
        icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO
        icon_type_icon = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO_I
        if level.type == LevelType.QUIZ:
            icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ
            icon_type_icon = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ_I
        content_type = get_content_type_srt(level.messages)
        content_text = get_content_text(level.messages)
        content_text = "\n—\n" + blockquote(content_text, expand=True) if content_text else ""
        date_create = datetime.fromtimestamp(level.date_create).strftime(strings.DATE_FORMAT_FULL)
        text = strings.LEVEL.format(type_icon=icon_type_str, index=level.order, level_name=level.title,
                                    data_create=date_create, training_name=cut_text(level.training.name),
                                    level_type=icon_type_str, content_type=content_type,
                                    level_type_icon=icon_type_icon) + content_text
        keyboard = level_keyboard(token, training_id, level_id, level.order, len(levels))
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except NotFoundError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_level(token: str, msg: Message, level_id: int, edited_msg_id: Optional[int] = None):
    try:
        level = await service.get_level_by_id(token, level_id)
        await send_msg(msg, level.messages)
    except ValueError as _:
        await show(msg, text=strings.LEVEL__ERROR__VIEW, edited_msg_id=edited_msg_id, is_answer=True)
    except NotFoundError:
        await show(msg, text=strings.LEVEL__NOT_FOUND, edited_msg_id=edited_msg_id, is_answer=True)


async def show_start_level(token: str, msg: Message, training_id: int, edited_msg_id: Optional[int] = None):
    try:
        training = await service.get_training_by_id(token, training_id)
        await send_msg(msg, training.message)
    except NotFoundError:
        await show(msg, text=strings.TRAINING__NOT_FOUND, edited_msg_id=edited_msg_id, is_answer=True)


async def show_about_start_level(token: str, msg: Message, training_id: int, edited_msg_id: Optional[int] = None,
                                 is_answer: bool = True):
    try:
        training = await service.get_training_by_id(token, training_id)
        content_text = "\n—\n" + blockquote(get_content_text(training.message), expand=True)
        has_preview = "🖼" if training.msg.content_type == ContentType.PHOTO else strings.EMPTY_FIELD
        text = strings.TRAINING__START_LEVEL.format(training_name=cut_text(training.name),
                                                    has_preview=has_preview) + content_text
        keyboard = training_start_keyboard(token, training_id)
        await show(msg, text, is_answer, edited_msg_id, keyboard=keyboard)
    except NotFoundError:
        await show_levels(token, training_id, msg, edited_msg_id, is_answer=False)


async def show_students(token: str, msg: Message, training_id: int, edited_msg_id: Optional[int] = None,
                        page_index: int = 0, is_answer: bool = True):
    try:
        training = await service.get_training_by_id(token, training_id)
        students = training.students
        list_items = [ListItem(str(i + 1), students[i].id, students[i]) for i in range(len(students))]
        pages = get_pages(list_items)
        keyboard = list_keyboard(token, TAG_STUDENTS, pages, page_index=page_index, back_btn_text=strings.BTN_BACK,
                                 arg=training_id)
        page_items = get_items_by_page(list_items, pages, page_index)
        student_items = []
        for item in page_items:
            student: StudentData = item.obj
            student_item = strings.STUDENT_ITEM.format(index=item.name, full_name=get_full_name_by_account(student))
            student_items.append(student_item)
        text = strings.STUDENTS.format(training_name=cut_text(training.name), items="\n".join(student_items))
        if not students:
            text = strings.STUDENTS__EMPTY.format(training_name=cut_text(training.name))
        await show(msg, text, is_answer, edited_msg_id, keyboard=keyboard)
    except NotFoundError:
        await show_training(token, training_id, msg, is_answer=False)
