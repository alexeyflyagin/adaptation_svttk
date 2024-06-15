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

from data.asvttk_service.exceptions import TokenNotValidError, AccessError, EmptyFieldError, NotFoundError
from data.asvttk_service.models import LevelType
from data.asvttk_service.types import TrainingData
from handlers.handlers_delete import DeleteItemCD, show_delete
from handlers.handlers_list import ListItem, get_pages, get_safe_page_index, list_keyboard, get_items_by_page, ListCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state
from data.asvttk_service import asvttk_service as service
from src import commands, strings
from src.states import MainStates, TrainingCreateStates, TrainingEditNameStates, LevelCreateStates
from src.utils import show, cut_text, get_training_status, CONTENT_TYPE__MEDIA_GROUP, UPDATED_MSG, UPDATED_ITEM_ID

router = Router()

TAG_TRAININGS = "trainings"
TAG_CHOOSE_ROLE = "choose_role"
TAG_TRAINING_DELETE = "training_del"
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


class TrainingStartCD(CallbackData, prefix="training_start"):
    token: str
    training_id: int
    action: int

    class Action:
        BACK = 0
        SHOW = 1


def training_keyboard(token: str, page_index: int, training_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if training_id:
        btn_levels_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                     action=TrainingCD.Action.LEVELS)
        btn_edit_name_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                        action=TrainingCD.Action.EDIT_NAME)
        btn_delete_data = TrainingCD(token=token, training_id=training_id, page_index=page_index,
                                     action=TrainingCD.Action.DELETE)
        kbb.add(InlineKeyboardButton(text=strings.BTN_LEVELS, callback_data=btn_levels_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_NAME, callback_data=btn_edit_name_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [2, 1]
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
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [1]
    btn_back_data = LevelCD(token=token, level_id=level_id, training_id=training_id, action=LevelCD.Action.BACK)
    kbb.add(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def training_start_keyboard(token: str, training_id: int):
    kbb = InlineKeyboardBuilder()
    adjust = []
    btn_show_data = TrainingStartCD(token=token, training_id=training_id, action=TrainingStartCD.Action.SHOW)
    kbb.add(InlineKeyboardButton(text=strings.BTN_SHOW, callback_data=btn_show_data.pack()))
    adjust += [1]
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
            training = await service.get_training_by_id(data.token, data.training_id)
            text = strings.TRAINING__DELETE.format(training_name=training.name)
            await show_delete(data.token, callback.message, tag=TAG_TRAINING_DELETE, deleted_item_id=data.training_id,
                              args=data.page_index, is_answer=False, text=text)
        elif data.action == data.Action.EDIT_NAME:
            await state.set_state(TrainingEditNameStates.NAME)
            await callback.message.answer(strings.TRAINING__EDIT_NAME)
            await state.update_data({UPDATED_ITEM_ID: data.training_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id, data.page_index]})
        elif data.action == data.Action.LEVELS:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
        await callback.answer()
    except NotFoundError:
        await show_training(data.token, data.training_id, callback.message, data.page_index, is_answer=False)
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
            await callback.message.answer(strings.CREATE_LEVEL__CONTENT)
            await reset_state(state)
            await state.set_state(LevelCreateStates.Content)
            await state.update_data({UPDATED_ITEM_ID: training_id})
            await state.update_data({UPDATED_MSG: [callback.message.message_id]})
        elif data.action == data.Action.SELECT and data.selected_item_id != -1:
            await show_level(data.token, callback.message, training_id, data.selected_item_id, is_answer=False)
        elif data.action == data.Action.SELECT and data.selected_item_id == -1:
            await show_level_start(data.token, callback.message, training_id, is_answer=False)
        await callback.answer()
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
            await show_level(data.token, callback.message, data.training_id, level.next_level_id, is_answer=False)
        elif data.action == data.Action.PREVIOUS_LEVEL and level.previous_level_id:
            await show_level(data.token, callback.message, data.training_id, level.previous_level_id, is_answer=False)
        elif data.action == data.Action.DELETE:
            level = await service.get_level_by_id(data.token, data.level_id)
            text = strings.LEVEL__DELETE.format(level_name=cut_text(level.title),
                                                training_name=cut_text(level.training.name))
            await show_delete(data.token, callback.message, data.level_id, text, TAG_DELETE_LEVEL, is_answer=False,
                              args=data.training_id)
        await callback.answer()
    except NotFoundError:
        await show_level(data.token, callback.message, data.training_id, data.level_id, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(DeleteItemCD.filter(F.tag == TAG_DELETE_LEVEL))
async def delete_level_callback(callback: CallbackQuery, state: FSMContext):
    data = DeleteItemCD.unpack(callback.data)
    training_id = int(data.args)
    try:
        await service.token_validate(data.token)
        if data.is_delete:
            level = await service.get_level_by_id(data.token, data.deleted_item_id)
            await service.delete_level_by_id(data.token, data.deleted_item_id)
            await show_levels(data.token, training_id, callback.message, is_answer=False)
            await callback.answer(strings.LEVEL__DELETED.format(level_name=cut_text(level.title)))
        else:
            await show_level(data.token, callback.message, training_id, data.deleted_item_id, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await show_level(data.token, callback.message, training_id, data.level_id, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(TrainingStartCD.filter())
async def level_callback(callback: CallbackQuery, state: FSMContext):
    data = TrainingStartCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_levels(data.token, data.training_id, callback.message, is_answer=False)
        await callback.answer()
    except NotFoundError:
        await show_levels(data.token, data.training_id, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


CREATE_LEVEL_CONTENT_TEXT = 'create_level_content_text'
CREATE_LEVEL_CONTENT_HTML_TEXT = 'create_level_content_html_text'
CREATE_LEVEL_CONTENT_TYPE = 'create_content_type'
CREATE_LEVEL_CONTENT_DOCUMENT_IDS = 'create_content_document_ids'
CREATE_LEVEL_CONTENT_PHOTO_IDS = 'create_content_photo_ids'
CREATE_LEVEL_CONTENT_VIDEO_IDS = 'create_content_video_ids'
CREATE_LEVEL_CONTENT_CORRECT_OPTION_IDS = 'create_content_correct_option_ids'
CREATE_LEVEL_CONTENT_OPTIONS = 'create_content_options'
CREATE_LEVEL_CONTENT_QUIZ_COMMENT = 'create_content_quiz_comment'


@router.message(LevelCreateStates.Content)
async def create_level_content_handler(msg: AlbumMessage, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        text = msg.text if msg.text else msg.caption
        html_text = msg.html_text if msg.html_text else None
        photo_ids = None
        video_ids = None
        document_ids = None
        options = None
        correct_option_ids = None
        quiz_comment = None
        if msg.content_type == ContentType.TEXT:
            level_type = LevelType.TEXT
        elif msg.content_type == ContentType.PHOTO:
            level_type = LevelType.PHOTO
            photo_ids = [msg.photo[-1].file_id]
        elif msg.content_type == ContentType.VIDEO:
            level_type = LevelType.VIDEO
            video_ids = [msg.video.file_id]
        elif msg.content_type == ContentType.DOCUMENT:
            level_type = LevelType.DOCUMENT
            document_ids = [msg.document.file_id]
        elif msg.content_type == ContentType.POLL and msg.poll.type == PollType.QUIZ:
            level_type = LevelType.QUIZ
            options = [i.text for i in msg.poll.options]
            correct_option_ids = [msg.poll.correct_option_id]
            quiz_comment = msg.poll.explanation
        elif msg.content_type == CONTENT_TYPE__MEDIA_GROUP:
            level_type = LevelType.MEDIA_GROUP
            c_document_ids = [i.document.file_id for i in msg.messages if i.content_type == ContentType.DOCUMENT]
            if c_document_ids:
                document_ids = c_document_ids
            c_photo_ids = [i.photo[-1].file_id for i in msg.messages if i.content_type == ContentType.PHOTO]
            if c_photo_ids:
                photo_ids = c_photo_ids
            c_video_ids = [i.video.file_id for i in msg.messages if i.content_type == ContentType.VIDEO]
            if c_video_ids:
                video_ids = c_video_ids
        else:
            await msg.answer(strings.CREATE_LEVEL__CONTENT__ERROR__INCORRECT_FORMAT)
            return
        await state.update_data({CREATE_LEVEL_CONTENT_TEXT: text, CREATE_LEVEL_CONTENT_HTML_TEXT: html_text,
                                 CREATE_LEVEL_CONTENT_TYPE: level_type, CREATE_LEVEL_CONTENT_OPTIONS: options,
                                 CREATE_LEVEL_CONTENT_PHOTO_IDS: photo_ids,
                                 CREATE_LEVEL_CONTENT_DOCUMENT_IDS: document_ids,
                                 CREATE_LEVEL_CONTENT_VIDEO_IDS: video_ids,
                                 CREATE_LEVEL_CONTENT_QUIZ_COMMENT: quiz_comment,
                                 CREATE_LEVEL_CONTENT_CORRECT_OPTION_IDS: correct_option_ids})
        await state.set_state(LevelCreateStates.Title)
        await msg.answer(strings.CREATE_LEVEL__TITLE)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.message(LevelCreateStates.Title)
async def create_level_title_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.CREATE_LEVEL__TITLE__ERROR__INCORRECT_FORMAT)
        return
    try:
        await service.token_validate(token)
        state_data = await state.get_data()
        title = msg.text
        training_id = state_data[UPDATED_ITEM_ID]
        await service.create_level(token,
                                   level_type=state_data[CREATE_LEVEL_CONTENT_TYPE],
                                   training_id=training_id,
                                   title=title, text=state_data[CREATE_LEVEL_CONTENT_TEXT],
                                   html_text=state_data[CREATE_LEVEL_CONTENT_HTML_TEXT],
                                   photo_ids=state_data[CREATE_LEVEL_CONTENT_PHOTO_IDS],
                                   video_ids=state_data[CREATE_LEVEL_CONTENT_VIDEO_IDS],
                                   document_ids=state_data[CREATE_LEVEL_CONTENT_DOCUMENT_IDS],
                                   options=state_data[CREATE_LEVEL_CONTENT_OPTIONS],
                                   correct_option_ids=state_data[CREATE_LEVEL_CONTENT_CORRECT_OPTION_IDS],
                                   quiz_comment=state_data[CREATE_LEVEL_CONTENT_QUIZ_COMMENT])
        await msg.answer(strings.CREATE_LEVEL__SUCCESS)
        updated_msg = state_data[UPDATED_MSG]
        if updated_msg:
            await show_levels(token, training_id, msg, edited_msg_id=updated_msg[0])
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
        list_item = [ListItem(strings.TRAININGS__LEVELS__ITEM__TYPE__START, item_id=-1)]
        list_item += [ListItem(str(i + 1), levels[i].id, levels[i]) for i in range(len(levels))]
        keyboard = list_keyboard(token, tag=TAG_LEVELS, pages=[list_item], max_btn_in_row=5, back_btn_text=strings.BTN_BACK,
                                 arg=training_id)
        items_str = [
            strings.TRAININGS__LEVELS__ITEM__NO_INDEX.format(
                type_icon=strings.TRAININGS__LEVELS__ITEM__TYPE__START,
                level_title=cut_text(training.start_text.strip()),
            )
        ]
        for item in list_item:
            if item.item_id == -1:
                continue
            icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO
            if item.obj.type == LevelType.QUIZ:
                icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ
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


async def show_level(token: str, msg: Message, training_id: int, level_id: int, edited_msg_id: Optional[int] = None,
                     is_answer: bool = True):
    text = strings.LEVEL__NOT_FOUND
    keyboard = level_keyboard(token, training_id)
    try:
        level = await service.get_level_by_id(token, level_id)
        levels = await service.get_levels_by_training(token, level.training_id)
        index = next((i for i in range(len(levels)) if levels[i].id == level.id)) + 1
        icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__INFO
        if level.type == LevelType.QUIZ:
            icon_type_str = strings.TRAININGS__LEVELS__ITEM__TYPE__QUIZ
        attached_counter = len(level.photo_ids) if level.photo_ids else 0
        attached_counter += len(level.video_ids) if level.video_ids else 0
        attached_counter += len(level.document_ids) if level.document_ids else 0
        content_text = level.text if level.text else strings.LEVEL__NO_TEXT
        text = strings.LEVEL.format(type_icon=icon_type_str, index=index, level_name=level.title,
                                    training_name=cut_text(level.training.name), level_type=icon_type_str,
                                    attached_counter=attached_counter, text=content_text)
        keyboard = level_keyboard(token, training_id, level_id, index, len(levels))
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except NotFoundError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_level_start(token: str, msg: Message, training_id: int, edited_msg_id: Optional[int] = None,
                           is_answer: bool = True):
    try:
        training = await service.get_training_by_id(token, training_id)
        text = strings.LEVEL__START.format(training_name=cut_text(training.name), text=training.start_text)
        keyboard = training_start_keyboard(token, training_id)
        await show(msg, text, is_answer, edited_msg_id, keyboard=keyboard)
    except NotFoundError:
        await show_levels(token, training_id, msg, edited_msg_id, is_answer=False)
