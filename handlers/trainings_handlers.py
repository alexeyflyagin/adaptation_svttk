import asyncio
from src.strings import eschtml, item_id
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ContentType, PollType
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_album import AlbumMessage

from data.asvttk_service.exceptions import (TokenNotValidError, AccessError, NotFoundError,
                                            TrainingAlreadyHasThisStateError, TrainingIsActiveError,
                                            TrainingIsNotActiveError,
                                            TrainingHasStudentsError, TrainingIsEmptyError, UnknownError,
                                            TrainingNotFoundError, NotChooseRoleError)
from data.asvttk_service.models import LevelType, AccountType
from data.asvttk_service.types import TrainingData, StudentData
from handlers.handlers_confirmation import ConfirmationCD, show_confirmation
from handlers.handlers_list import ListItem, get_pages, get_safe_page_index, list_keyboard, get_items_by_page, ListCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state, \
    send_msg, get_content_text, unknown_error, unknown_error_for_callback, set_updated_msg, access_error_for_callback, \
    set_updated_item, get_updated_item, get_updated_msg, access_error, get_content_type_str, delete_msg
from data.asvttk_service import asvttk_service as service
from handlers.value_validators import valid_content_type_msg, valid_full_name, ValueNotValidError, valid_name, \
    valid_one_msg
from middlewares.one_message_middleware import OneMessageMiddleware
from src import commands, strings
from src.keyboards import invite_keyboard
from src.states import MainStates, TrainingCreateStates, TrainingEditNameStates, LevelCreateStates, \
    TrainingStartEditStates, LevelEditStates, StudentCreateState
from src.strings import blockquote
from src.time_utils import get_date_str, DateFormat
from src.utils import show, ellipsis_text, get_training_status, CONTENT_TYPE__MEDIA_GROUP, \
    get_level_type_from_content_type, is_started_training, get_full_name_by_account, get_access_key_link, \
    CONTENT_TYPE__POLL__QUIZ, get_student_state_str

router = Router()
OneMessageMiddleware(router, one_message_states=[LevelCreateStates.CONTENT, LevelEditStates.CONTENT])

TAG_TRAININGS = "trains"
TAG_STUDENTS = "stud"
TAG_CHOOSE_ROLE = "ch_role"
TAG_TRAINING_DELETE = "t_del"
TAG_TRAINING_START = "t_st"
TAG_TRAINING_STOP = "t_en"
TAG_LEVELS = "l"
TAG_DELETE_LEVEL = "l_del"

NEW_TRAINING_NAME = "new_training_name"
NEW_LEVEL_TITLE = "new_level_title"


class TrainingCD(CallbackData, prefix="t"):
    token: str
    training_id: Optional[int] = None
    action: int

    class Action:
        BACK = 0
        DELETE = 1
        EDIT_NAME = 2
        LEVELS = 3
        START = 4
        STOP = 5
        STUDENTS = 6
        REPORT = 7


class LevelCD(CallbackData, prefix="l"):
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


class StartLevelCD(CallbackData, prefix="st_l"):
    token: str
    training_id: int
    action: int

    class Action:
        BACK = 0
        SHOW = 1
        EDIT = 2


class StudentCD(CallbackData, prefix="stud"):
    token: str
    training_id: int
    student_id: Optional[int] = None
    action: int

    class Action:
        BACK = 0
        DELETE = 1
        EDIT_FN = 2


def training_keyboard(token: str, training_id: Optional[int] = None, is_started: bool = False,
                      student_counter: Optional[int] = None, level_counter: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if training_id:
        if is_started:
            btn_stop_data = TrainingCD(token=token, training_id=training_id, action=TrainingCD.Action.STOP)
            kbb.add(InlineKeyboardButton(text=strings.BTN_TRAINING_STOP, callback_data=btn_stop_data.pack()))
        else:
            btn_start_data = TrainingCD(token=token, training_id=training_id, action=TrainingCD.Action.START)
            kbb.add(InlineKeyboardButton(text=strings.BTN_TRAINING_START, callback_data=btn_start_data.pack()))
        adjust += [1]
        btn_report_data = TrainingCD(token=token, training_id=training_id, action=TrainingCD.Action.REPORT)
        kbb.add(InlineKeyboardButton(text=strings.BTN_REPORT, callback_data=btn_report_data.pack()))
        adjust += [1]
        btn_students_data = TrainingCD(token=token, training_id=training_id, action=TrainingCD.Action.STUDENTS)
        btn_levels_data = TrainingCD(token=token, training_id=training_id, action=TrainingCD.Action.LEVELS)
        btn_edit_name_data = TrainingCD(token=token, training_id=training_id, action=TrainingCD.Action.EDIT_NAME)
        btn_delete_data = TrainingCD(token=token, training_id=training_id, action=TrainingCD.Action.DELETE)
        kbb.add(InlineKeyboardButton(text=strings.BTN_STUDENTS + f" ({student_counter})",
                                     callback_data=btn_students_data.pack()))
        kbb.add(
            InlineKeyboardButton(text=strings.BTN_LEVELS + f" ({level_counter})", callback_data=btn_levels_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_NAME, callback_data=btn_edit_name_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [2, 1, 1]
    btn_back_data = TrainingCD(token=token, action=TrainingCD.Action.BACK)
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
    btn_show_data = StartLevelCD(token=token, training_id=training_id, action=StartLevelCD.Action.SHOW)
    btn_edit_text_data = StartLevelCD(token=token, training_id=training_id, action=StartLevelCD.Action.EDIT)
    kbb.add(InlineKeyboardButton(text=strings.BTN_SHOW, callback_data=btn_show_data.pack()))
    kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT, callback_data=btn_edit_text_data.pack()))
    adjust += [1, 1]
    btn_back_data = StartLevelCD(token=token, training_id=training_id, action=LevelCD.Action.BACK)
    kbb.add(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def student_keyboard(token: str, training_id: int, student_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if student_id:
        btn_edit_fn_data = StudentCD(token=token, training_id=training_id, student_id=student_id,
                                     action=StudentCD.Action.EDIT_FN)
        btn_delete_data = StudentCD(token=token, training_id=training_id, student_id=student_id,
                                    action=StudentCD.Action.DELETE)
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_FULL_NAME, callback_data=btn_edit_fn_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [1, 1]
    btn_back_data = StudentCD(token=token, training_id=training_id, action=StudentCD.Action.BACK)
    kbb.add(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust += [1]
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
    except UnknownError:
        await unknown_error(msg, state, canceled=False)


@router.callback_query(ListCD.filter(F.tag == TAG_TRAININGS))
async def trainings_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.ADD:
            await state.set_state(TrainingCreateStates.NAME)
            await callback.message.answer(strings.CREATE_TRAINING__NAME)
            await set_updated_msg(state, callback.message.message_id)
        elif data.action == data.Action.SELECT:
            await show_training(data.token, data.selected_item_id, callback.message, is_answer=False)
        elif data.action == data.Action.PREVIOUS_PAGE:
            await show_trainings(data.token, callback.message, page_index=data.page_index - 1, is_answer=False)
        elif data.action == data.Action.NEXT_PAGE:
            await show_trainings(data.token, callback.message, page_index=data.page_index + 1, is_answer=False)
        elif data.action == data.Action.COUNTER:
            await show_trainings(data.token, callback.message, page_index=data.page_index, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(TrainingCD.filter())
async def training_callback(callback: CallbackQuery, state: FSMContext):
    data = TrainingCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_trainings(data.token, callback.message, is_answer=False)
            await callback.answer()
        elif data.action == data.Action.DELETE:
            await service.check_training_is_not_active(data.token, data.training_id)
            await service.check_training_has_not_students(data.token, data.training_id)
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__DELETE.format(training_name=eschtml(training.name))
            await show_confirmation(data.token, callback.message, tag=TAG_TRAINING_DELETE,
                                    item_id=data.training_id, is_answer=False, text=text)
            await callback.answer()
        elif data.action == data.Action.EDIT_NAME:
            await service.check_training_is_not_active(data.token, data.training_id)
            await service.check_training_has_not_students(data.token, data.training_id)
            await state.set_state(TrainingEditNameStates.NAME)
            await callback.message.answer(strings.TRAINING__EDIT_NAME)
            await set_updated_item(state, data.training_id)
            await set_updated_msg(state, callback.message.message_id)
            await callback.answer()
        elif data.action == data.Action.LEVELS:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
            await callback.answer()
        elif data.action == data.Action.START:
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__START.format(training_name=eschtml(training.name))
            await show_confirmation(data.token, callback.message, data.training_id, text, tag=TAG_TRAINING_START,
                                    is_answer=False)
            await callback.answer()
        elif data.action == data.Action.STOP:
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__STOP.format(training_name=eschtml(training.name))
            await show_confirmation(data.token, callback.message, data.training_id, text, tag=TAG_TRAINING_STOP,
                                    is_answer=False)
            await callback.answer()
        elif data.action == data.Action.STUDENTS:
            await show_students(data.token, callback.message, data.training_id, is_answer=False)
            await callback.answer()
        elif data.action == data.Action.REPORT:
            await callback.answer()
            await show_training_report(data.token, data.training_id, callback.message)
    except TrainingHasStudentsError:
        await callback.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except AccessError:
        await access_error_for_callback(callback, state)
    except (NotFoundError, TrainingNotFoundError):
        await show_training(data.token, data.training_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ListCD.filter(F.tag == TAG_STUDENTS))
async def students_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    training_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_training(data.token, training_id, callback.message, is_answer=False)
        elif data.action == data.Action.ADD:
            await service.check_training_is_active(data.token, training_id)
            await reset_state(state)
            await callback.message.answer(strings.STUDENTS__ENTER__FULL_NAME)
            await state.set_state(StudentCreateState.FULL_NAME)
            await set_updated_item(state, training_id)
            await set_updated_msg(state, callback.message.message_id)
        elif data.action == data.Action.SELECT:
            await show_student(data.token, training_id, data.selected_item_id, callback.message, is_answer=False)
        elif data.action == data.Action.NEXT_PAGE:
            await show_students(data.token, callback.message, training_id, page_index=data.page_index + 1,
                                is_answer=False)
        elif data.action == data.Action.PREVIOUS_PAGE:
            await show_students(data.token, callback.message, training_id, page_index=data.page_index - 1,
                                is_answer=False)
        elif data.action == data.Action.COUNTER:
            await show_students(data.token, callback.message, training_id, page_index=data.page_index,
                                is_answer=False)
        await callback.answer()
    except TrainingNotFoundError:
        await show_training(data.token, training_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
    except TrainingIsNotActiveError:
        await callback.answer(strings.TRAINING_IS_NOT_STARTED_ERROR)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(StudentCD.filter())
async def student_callback(callback: CallbackQuery, state: FSMContext):
    data = StudentCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_students(data.token, callback.message, data.training_id, callback.message.message_id,
                                is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.message(StudentCreateState.FULL_NAME)
async def create_student_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        last_name, first_name, patronymic = valid_full_name(msg.text, null_if_empty=True)
        updated_item_id, args = await get_updated_item(state)
        acc_data = await service.create_student(token, updated_item_id, first_name, last_name, patronymic)
        training = await service.get_training_by_id(token, updated_item_id)
        keyboard = invite_keyboard(AccountType.STUDENT, acc_data.access_key)
        text = strings.CREATE_STUDENT__SUCCESS.format(access_key=acc_data.access_key,
                                                      access_link=get_access_key_link(acc_data.access_key))
        await msg.answer(text, reply_markup=keyboard)
        await reset_state(state)
        await asyncio.sleep(0.5)
        updated_msg_id, updated_msg_args = await get_updated_msg(state)
        await show_students(token, msg, training.id, edited_msg_id=updated_msg_id, is_answer=True)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(error_msg=e.error_msg))
    except TrainingIsNotActiveError:
        await msg.answer(strings.TRAINING_IS_NOT_STARTED_ERROR)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except (NotFoundError, TrainingNotFoundError):
        await msg.answer(strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_TRAINING_START))
async def start_training_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            await service.start_training(data.token, data.item_id)
            await show_training(data.token, data.item_id, callback.message, is_answer=False)
            await callback.answer(strings.TRAINING__STARTED)
        else:
            await show_training(data.token, data.item_id, callback.message, is_answer=False)
            await callback.answer()
    except TrainingIsEmptyError:
        await callback.answer(strings.TRAINING__STARTED__ERROR__TRAINING_IS_EMPTY)
    except AccessError:
        await access_error_for_callback(callback, state)
    except NotFoundError:
        await show_training(data.token, data.item_id, callback.message, is_answer=False)
    except TrainingAlreadyHasThisStateError:
        await callback.answer(strings.TRAINING__STARTED__ERROR__ALREADY_STARTED)
        await show_training(data.token, data.item_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_TRAINING_STOP))
async def stop_training_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            await service.stop_training(data.token, data.item_id)
            await show_training(data.token, data.item_id, callback.message, is_answer=False)
            await callback.answer(strings.TRAINING__STOPPED)
        else:
            await show_training(data.token, data.item_id, callback.message, is_answer=False)
            await callback.answer()
    except AccessError:
        await access_error_for_callback(callback, state)
    except NotFoundError:
        await show_training(data.token, data.item_id, callback.message, is_answer=False)
        await callback.answer()
    except TrainingAlreadyHasThisStateError:
        await callback.answer(strings.TRAINING__STARTED__ERROR__NOT_STARTED)
        await show_training(data.token, data.item_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_TRAINING_DELETE))
async def delete_training_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            await service.delete_training(data.token, data.item_id)
            await show_trainings(data.token, callback.message, is_answer=False)
            await callback.answer(strings.TRAINING__DELETED)
        else:
            await show_training(data.token, data.item_id, callback.message, is_answer=False)
            await callback.answer()
    except AccessError:
        await access_error_for_callback(callback, state)
    except TrainingHasStudentsError:
        await callback.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except NotFoundError:
        await show_training(data.token, data.item_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.message(TrainingCreateStates.NAME, F.content_type == ContentType.TEXT)
async def create_training_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        name = valid_name(msg.text)
        await service.create_training(token, name)
        await msg.answer(strings.CREATE_TRAINING__CREATED)
        await reset_state(state)
        updated_msg_id, updated_msg_args = await get_updated_msg(state)
        await show_trainings(token, msg, edited_msg_id=updated_msg_id)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except NotChooseRoleError:
        await state.set_state(TrainingCreateStates.ROLE)
        name = valid_name(msg.text)
        await state.update_data({NEW_TRAINING_NAME: name})
        await show_choose_role(token, msg)
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.callback_query(ListCD.filter(F.tag == TAG_CHOOSE_ROLE))
async def create_training_role_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    state_state = await state.get_state()
    if state_state not in TrainingCreateStates.__all_states_names__:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer(strings.ACTION_CANCELED)
        return
    try:
        await service.token_validate(data.token)
        state_data = await state.get_data()
        name = state_data.get(NEW_TRAINING_NAME)
        await service.create_training(data.token, name, role_id=data.selected_item_id)
        role = await service.get_role_by_id(data.token, data.selected_item_id)
        await callback.message.edit_text(strings.CREATE_TRAINING__ROLE__SELECTED.format(role_name=eschtml(role.name)))
        await callback.message.answer(strings.CREATE_TRAINING__CREATED)
        await reset_state(state)
        updated_msg_id, updated_msg_arg = await get_updated_msg(state)
        await show_trainings(data.token, callback.message, edited_msg_id=updated_msg_id)
        await callback.answer()
    except AccessError:
        await access_error(callback.message, state)
        await callback.message.edit_reply_markup(reply_markup=None)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error(callback.message, state)
        await callback.message.edit_reply_markup(reply_markup=None)


@router.message(TrainingEditNameStates.NAME)
async def edit_name_training_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        name = valid_name(msg.text)
        employee_id, args = await get_updated_item(state)
        await service.update_name_training(token, employee_id, name=name)
        await msg.answer(strings.TRAINING__EDIT_NAME__SUCCESS)
        await reset_state(state)
        update_msg_id, update_msg_args = await get_updated_msg(state)
        await show_training(token, employee_id, msg, edited_msg_id=update_msg_id)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except TrainingHasStudentsError:
        await msg.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except NotFoundError:
        await msg.answer(text=strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.callback_query(ListCD.filter(F.tag == TAG_LEVELS))
async def levels_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    training_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_training(data.token, training_id, callback.message, is_answer=False)
        elif data.action == data.Action.ADD:
            await service.check_training_is_not_active(data.token, training_id)
            await service.check_training_has_not_students(data.token, training_id)
            await callback.message.answer(strings.ENTER__LEVEL__TITLE)
            await state.set_state(LevelCreateStates.TITLE)
            await set_updated_item(state, training_id)
            await set_updated_msg(state, callback.message.message_id)
        elif data.action == data.Action.SELECT and data.selected_item_id != -1:
            await show_about_level(data.token, callback.message, training_id, data.selected_item_id, is_answer=False)
        elif data.action == data.Action.SELECT and data.selected_item_id == -1:
            await show_about_start_level(data.token, callback.message, training_id, is_answer=False)
        await callback.answer()
    except TrainingHasStudentsError:
        await callback.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except TrainingNotFoundError:
        await show_training(data.token, training_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(LevelCD.filter())
async def level_callback(callback: CallbackQuery, state: FSMContext):
    data = LevelCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
        else:
            level = await service.get_level_by_id(data.token, data.level_id)
            if data.action == data.Action.NEXT_LEVEL and level.next_level_id:
                await show_about_level(data.token, callback.message, data.training_id, level.next_level_id,
                                       is_answer=False)
            elif data.action == data.Action.PREVIOUS_LEVEL and level.previous_level_id:
                await show_about_level(data.token, callback.message, data.training_id, level.previous_level_id,
                                       is_answer=False)
            elif data.action == data.Action.DELETE:
                await service.check_training_is_not_active(data.token, data.training_id)
                await service.check_training_has_not_students(data.token, data.training_id)
                level = await service.get_level_by_id(data.token, data.level_id)
                text = strings.LEVEL__DELETE.format(level_name=eschtml(ellipsis_text(level.title)),
                                                    training_name=eschtml(ellipsis_text(level.training.name)))
                await show_confirmation(data.token, callback.message, data.level_id, text, TAG_DELETE_LEVEL,
                                        is_answer=False,
                                        args=data.training_id)
            elif data.action == data.Action.COUNTER:
                await show_level(data.token, callback.message, data.level_id)
            elif data.action == data.Action.EDIT:
                await service.check_training_is_not_active(data.token, data.training_id)
                await service.check_training_has_not_students(data.token, data.training_id)
                await callback.message.answer(strings.ENTER__LEVEL_CONTENT)
                await state.set_state(LevelEditStates.CONTENT)
                await set_updated_item(state, data.level_id, [data.training_id])
                await set_updated_msg(state, callback.message.message_id)
            elif data.action == data.Action.EDIT_TITLE:
                await service.check_training_is_not_active(data.token, data.training_id)
                await service.check_training_has_not_students(data.token, data.training_id)
                await callback.message.answer(strings.ENTER__LEVEL__TITLE)
                await state.set_state(LevelEditStates.TITLE)
                await set_updated_item(state, data.level_id, [data.training_id])
                await set_updated_msg(state, callback.message.message_id)
        await callback.answer()
    except TrainingHasStudentsError:
        await callback.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except TrainingNotFoundError:
        await show_training(data.token, data.training_id, callback.message, is_answer=False)
    except NotFoundError:
        await show_about_level(data.token, callback.message, data.training_id, data.level_id, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


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
            await callback.answer(strings.LEVEL__DELETED.format(level_name=eschtml(ellipsis_text(level.title))))
        else:
            await show_about_level(data.token, callback.message, training_id, data.item_id, is_answer=False)
            await callback.answer()
    except TrainingHasStudentsError:
        await callback.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except AccessError:
        await access_error_for_callback(callback, state)
    except NotFoundError:
        await show_about_level(data.token, callback.message, training_id, data.level_id, is_answer=False)
    except TrainingNotFoundError:
        await show_training(data.token, training_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.message(LevelEditStates.TITLE)
async def edit_level_title_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        title = valid_name(msg.text)
        level_id, args = await get_updated_item(state)
        training_id = args[0]
        await service.update_title_level_by_id(token, level_id, title)
        await msg.answer(strings.EDIT_TITLE_LEVEL__SUCCESS)
        await reset_state(state)
        updated_msg_id, updated_msg_args = await get_updated_msg(state)
        await show_about_level(token, msg, training_id, level_id, edited_msg_id=updated_msg_id)
    except TrainingHasStudentsError:
        await msg.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except NotFoundError:
        await msg.answer(text=strings.LEVEL__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.message(LevelEditStates.CONTENT)
async def edit_level_content_handler(msg: Message | AlbumMessage, state: FSMContext, msg_count: int):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_one_msg(msg_count)
        valid_content_type_msg(msg, CONTENT_TYPE__MEDIA_GROUP, ContentType.TEXT, ContentType.AUDIO, ContentType.VIDEO,
                               ContentType.PHOTO, ContentType.DOCUMENT, ContentType.LOCATION, ContentType.ANIMATION,
                               ContentType.CONTACT, ContentType.STICKER, CONTENT_TYPE__POLL__QUIZ)
        if msg.content_type == ContentType.POLL and msg.poll.type == PollType.QUIZ:
            level_type = get_level_type_from_content_type(msg.content_type, PollType.QUIZ)
        else:
            level_type = get_level_type_from_content_type(msg.content_type)
        level_id, args = await get_updated_item(state)
        training_id = args[0]
        messages = msg.messages if msg.content_type == CONTENT_TYPE__MEDIA_GROUP else [msg]
        await service.update_content_level_by_id(token, level_type=level_type, level_id=level_id, messages=messages)
        await msg.answer(strings.EDIT_CONTENT_LEVEL__SUCCESS)
        await reset_state(state)
        updated_msg_id, updated_msg_args = await get_updated_msg(state)
        await show_about_level(token, msg, training_id, level_id, edited_msg_id=updated_msg_id)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except TrainingHasStudentsError:
        await msg.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except NotFoundError:
        await msg.answer(text=strings.LEVEL__NOT_FOUND)
        await reset_state(state)
    except TrainingNotFoundError:
        await msg.answer(text=strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.callback_query(StartLevelCD.filter())
async def start_level_callback(callback: CallbackQuery, state: FSMContext):
    data = StartLevelCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
        elif data.action == data.Action.SHOW:
            await show_start_level(data.token, callback.message, data.training_id)
        elif data.action == data.Action.EDIT:
            await service.check_training_is_not_active(data.token, data.training_id)
            await service.check_training_has_not_students(data.token, data.training_id)
            await callback.message.answer(strings.TRAINING__START__EDIT__CONTENT)
            await state.set_state(TrainingStartEditStates.CONTENT)
            await set_updated_item(state, data.training_id)
            await set_updated_msg(state, callback.message.message_id)
        await callback.answer()
    except TrainingHasStudentsError:
        await callback.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
    except TrainingIsActiveError:
        await callback.answer(strings.TRAINING_IS_STARTED_ERROR)
    except TrainingNotFoundError:
        await show_training(data.token, data.training_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.message(TrainingStartEditStates.CONTENT)
async def edit_start_level_handler(msg: AlbumMessage, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT, ContentType.PHOTO)
        training_id, args = await get_updated_item(state)
        messages = msg.messages if msg.content_type == CONTENT_TYPE__MEDIA_GROUP else [msg]
        await service.update_start_msg_training(token, training_id=training_id, msg=messages)
        await msg.answer(strings.TRAINING__START__EDIT__CONTENT__SUCCESS)
        await reset_state(state)
        updated_msg_id, updated_msg_args = await get_updated_msg(state)
        await show_about_start_level(token, msg, training_id, edited_msg_id=updated_msg_id)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except TrainingHasStudentsError:
        await msg.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except TrainingNotFoundError:
        await msg.answer(strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.message(LevelCreateStates.TITLE)
async def create_level_title_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        title = valid_name(msg.text)
        await state.update_data({NEW_LEVEL_TITLE: title})
        await state.set_state(LevelCreateStates.CONTENT)
        await msg.answer(strings.ENTER__LEVEL_CONTENT)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.message(LevelCreateStates.CONTENT)
async def create_level_content_handler(msg: AlbumMessage | Message, state: FSMContext, msg_count: int):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_one_msg(msg_count)
        valid_content_type_msg(msg, CONTENT_TYPE__MEDIA_GROUP, ContentType.TEXT, ContentType.AUDIO, ContentType.VIDEO,
                               ContentType.PHOTO, ContentType.DOCUMENT, ContentType.LOCATION, ContentType.ANIMATION,
                               ContentType.CONTACT, ContentType.STICKER, CONTENT_TYPE__POLL__QUIZ)
        if msg.content_type == ContentType.POLL and msg.poll.type == PollType.QUIZ:
            level_type = get_level_type_from_content_type(msg.content_type, PollType.QUIZ)
        else:
            level_type = get_level_type_from_content_type(msg.content_type)
        state_data = await state.get_data()
        title = state_data[NEW_LEVEL_TITLE]
        training_id, args = await get_updated_item(state)
        messages = msg.messages if msg.content_type == CONTENT_TYPE__MEDIA_GROUP else [msg]
        await service.create_level(token, level_type=level_type, training_id=training_id, title=title,
                                   messages=messages)
        await msg.answer(strings.CREATE_LEVEL__SUCCESS)
        await reset_state(state)
        updated_msg_id, updated_msg_args = await get_updated_msg(state)
        await show_levels(token, training_id, msg, edited_msg_id=updated_msg_id)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except TrainingHasStudentsError:
        await msg.answer(strings.TRAINING_HAS_STUDENTS_ERROR)
        await reset_state(state)
    except TrainingIsActiveError:
        await msg.answer(strings.TRAINING_IS_STARTED_ERROR)
        await reset_state(state)
    except TrainingNotFoundError:
        await msg.answer(strings.TRAINING__NOT_FOUND)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


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
                title=eschtml(ellipsis_text(trainings[i].name)),
                status=get_training_status(trainings[i]),
                student_counter=len(trainings[i].students),
            ))
        text = "\n\n".join(str_items)
        if not trainings:
            text = strings.TRAININGS__EMPTY
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_training(token: str, training_id: int, msg: Message, edited_msg_id: Optional[int] = None,
                        is_answer: bool = True):
    text = strings.TRAINING__NOT_FOUND
    keyboard = training_keyboard(token)
    try:
        training = await service.get_training_by_id(token, training_id)
        keyboard = training_keyboard(token, training_id, is_started=is_started_training(training),
                                     student_counter=len(training.students), level_counter=len(training.levels))
        text = strings.TRAINING.format(
            item_id=item_id(training.id),
            name=eschtml(training.name),
            students_counter=len(training.students),
            status=get_training_status(training),
            data_create=get_date_str(training.date_create, DateFormat.FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE),
        )
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except NotFoundError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        text = strings.ERROR__ACCESS
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_choose_role(token: str, msg: Message, edited_msg_id: Optional[int] = None, is_answer: bool = True):
    try:
        text = strings.CREATE_TRAINING__ROLE
        all_roles = await service.get_all_roles(token)
        list_items = [ListItem(i.name, i.id) for i in all_roles]
        keyboard = list_keyboard(token, tag=TAG_CHOOSE_ROLE, pages=[list_items], max_btn_in_row=2,
                                 add_btn_text=None)
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except NotFoundError:
        raise TokenNotValidError()


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
                level_title=eschtml(ellipsis_text(get_content_text(training.message).strip())),
            )
        ]
        for item in list_item:
            if item.item_id == -1:
                continue
            icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO_I
            if item.obj.type == LevelType.CONTROL:
                icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ_I
            item_str = strings.TRAININGS__LEVELS__ITEM.format(
                type_icon=icon_type_str,
                index=item.name,
                level_title=eschtml(ellipsis_text(item.obj.title)),
            )
            items_str.append(item_str)
        text = strings.TRAINING__LEVELS.format(training_name=eschtml(ellipsis_text(training.name)),
                                               items="\n".join(items_str))
        await show(msg, text=text, is_answer=is_answer, edited_msg_id=edited_msg_id, keyboard=keyboard)
    except (AccessError, NotFoundError):
        await show_training(token, training_id, msg, is_answer=is_answer)


async def show_about_level(token: str, msg: Message, training_id: int, level_id: int,
                           edited_msg_id: Optional[int] = None, is_answer: bool = True):
    text = strings.LEVEL__NOT_FOUND
    keyboard = level_keyboard(token, training_id)
    try:
        level = await service.get_level_by_id(token, level_id)
        levels = await service.get_levels_by_training(token, level.training_id)
        icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO
        icon_type_icon = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO_I
        if level.type == LevelType.CONTROL:
            icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ
            icon_type_icon = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ_I
        content_type = get_content_type_str(level.messages)
        content_text = eschtml(get_content_text(level.messages))
        content_text = "\n—\n" + blockquote(content_text, expand=True) if content_text else ""
        date_create = get_date_str(level.date_create, DateFormat.FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE)
        text = strings.LEVEL.format(type_icon=icon_type_str, index=level.order, level_name=eschtml(level.title),
                                    data_create=date_create, training_name=eschtml(ellipsis_text(level.training.name)),
                                    level_type=icon_type_str, content_type=content_type,
                                    level_type_icon=icon_type_icon, item_id=item_id(level.id)) + content_text
        keyboard = level_keyboard(token, training_id, level_id, level.order, len(levels))
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        text = strings.ERROR__ACCESS
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except NotFoundError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_level(token: str, msg: Message, level_id: int, edited_msg_id: Optional[int] = None):
    try:
        level = await service.get_level_by_id(token, level_id)
        await send_msg(msg, level.messages)
    except AccessError:
        await show(msg, strings.ERROR__ACCESS, edited_msg_id=edited_msg_id, is_answer=True)
    except NotFoundError:
        await show(msg, strings.LEVEL__NOT_FOUND, edited_msg_id=edited_msg_id, is_answer=True)


async def show_start_level(token: str, msg: Message, training_id: int, edited_msg_id: Optional[int] = None):
    try:
        training = await service.get_training_by_id(token, training_id)
        await send_msg(msg, training.message)
    except (NotFoundError, AccessError):
        await show_training(token, training_id, msg, edited_msg_id=edited_msg_id, is_answer=False)


async def show_about_start_level(token: str, msg: Message, training_id: int, edited_msg_id: Optional[int] = None,
                                 is_answer: bool = True):
    try:
        training = await service.get_training_by_id(token, training_id)
        content_text = "\n—\n" + blockquote(eschtml(get_content_text(training.message)), expand=True)
        has_preview = "🖼" if training.msg.content_type == ContentType.PHOTO else strings.EMPTY_FIELD
        text = strings.TRAINING__START_LEVEL.format(training_name=eschtml(ellipsis_text(training.name)),
                                                    has_preview=has_preview) + content_text
        keyboard = training_start_keyboard(token, training_id)
        await show(msg, text, is_answer, edited_msg_id, keyboard=keyboard)
    except (NotFoundError, AccessError):
        await show_training(token, training_id, msg, edited_msg_id, is_answer=False)


async def show_students(token: str, msg: Message, training_id: int, edited_msg_id: Optional[int] = None,
                        page_index: int = 0, is_answer: bool = True):
    try:
        progresses = await service.get_all_student_progresses(token, training_id)
        training = await service.get_training_by_id(token, training_id)
        list_items = [ListItem(str(i + 1), progresses[i].student.id, progresses[i]) for i in range(len(progresses))]
        pages = get_pages(list_items)
        page_index = get_safe_page_index(page_index, len(pages))
        keyboard = list_keyboard(token, TAG_STUDENTS, pages, page_index=page_index, back_btn_text=strings.BTN_BACK,
                                 arg=training_id)
        page_items = get_items_by_page(list_items, pages, page_index)
        student_items = []
        for item in page_items:
            student: StudentData = item.obj.student
            progress_percent = round(len(item.obj.answers) / len(item.obj.training.levels) * 100)
            state = get_student_state_str(item.obj.progress_state)
            student_item = strings.STUDENT_ITEM.format(index=item.name,
                                                       full_name=eschtml(get_full_name_by_account(student)),
                                                       state=state, progress_percent=progress_percent)
            student_items.append(student_item)
        text = strings.STUDENTS.format(training_name=eschtml(ellipsis_text(training.name)),
                                       items="\n\n".join(student_items))
        if not progresses:
            text = strings.STUDENTS__EMPTY.format(training_name=eschtml(ellipsis_text(training.name)))
        await show(msg, text, is_answer, edited_msg_id, keyboard=keyboard)
    except (TrainingNotFoundError, NotFoundError, AccessError):
        await show_training(token, training_id, msg, is_answer=False)


async def show_student(token: str, training_id: int, student_id: int, msg: Message, edited_msg_id: Optional[int] = None,
                       is_answer: bool = True):
    text = strings.STUDENT_NOT_FOUND
    keyboard = student_keyboard(token, training_id)
    try:
        progress = await service.get_student_progress(token, student_id)
        student: StudentData = progress.student
        progress_percent = round(len(progress.answers) / len(progress.training.levels) * 100)
        text = strings.STUDENT.format(
            last_name=eschtml(student.last_name), first_name=eschtml(student.first_name), item_id=item_id(student.id),
            patronymic=eschtml(student.patronymic), state=get_student_state_str(progress.progress_state),
            date_create=get_date_str(student.date_create, DateFormat.FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE),
            answer_count=len(progress.answers), level_count=len(progress.training.levels),
            progress_percent=progress_percent,
        )
        keyboard = student_keyboard(token, training_id, student_id)
        await show(msg, text, edited_msg_id=edited_msg_id, keyboard=keyboard, is_answer=False)
    except NotFoundError:
        await show(msg, text, edited_msg_id=edited_msg_id, keyboard=keyboard, is_answer=False)
    except AccessError:
        text = strings.ERROR__ACCESS
        await show(msg, text, edited_msg_id=edited_msg_id, keyboard=keyboard, is_answer=False)


async def show_training_report(token: str, training_id: int, msg: Message):
    bot_msg = await msg.answer(text=strings.WAIT_OF_REPORT_GENERATING)
    try:
        report_data = await service.get_training_report(token, training_id)
        training = await service.get_training_by_id(token, training_id)
        try:
            account = await service.get_account_by_token(token)
        except NotFoundError:
            raise TokenNotValidError()
        file = FSInputFile(path=report_data.report_file.__absolute_path__)
        caption = strings.REPORT_TRAINING.format(
            date_create=get_date_str(report_data.date_create, DateFormat.FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE),
            training_name=eschtml(ellipsis_text(training.name)), training_id=training_id,
            full_name=eschtml(get_full_name_by_account(account, full_patronymic=True)),
        )
        await msg.answer_document(document=file, caption=caption)
        await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
        report_data.report_file.delete()
    except (TrainingNotFoundError, NotFoundError):
        await show(msg, text=strings.TRAINING__NOT_FOUND, is_answer=True)
        await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
    except AccessError:
        await show(msg, text=strings.ERROR__ACCESS, is_answer=True)
        await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
    except UnknownError:
        await show(msg, text=strings.ERROR__UNKNOWN, is_answer=True)
        await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
