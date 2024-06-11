from typing import Optional, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from data.asvttk_service.exceptions import TokenNotValidError, AccessError, EmptyFieldError
from data.asvttk_service.types import TrainingData
from handlers.handlers_list import ListItem, get_pages, get_safe_page_index, list_keyboard, get_items_by_page, ListCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state
from data.asvttk_service import asvttk_service as service
from src import commands, strings
from src.states import MainStates, TrainingCreateStates
from src.utils import show, cut_text, get_training_status

router = Router()

TAG_TRAININGS = "trainings"
TAG_CHOOSE_ROLE = "choose_role"


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
            await callback.answer()
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
    if state_state != TrainingCreateStates.ROLE:
        await callback.message.edit_reply_markup(reply_markup=None)
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


async def show_trainings(token: str, msg: Message, page_index: int = 0, edited_msg_id: Optional[int] = None,
                         is_answer: bool = True):
    text = strings.TRAININGS__UNAVAILABLE
    keyboard = None
    try:
        trainings = await service.get_all_my_trainings(token)
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


async def show_choose_role(token: str, msg: Message, edited_msg_id: Optional[int] = None, page_index: int = 0,
                           is_answer: bool = True):
    text = strings.CREATE_TRAINING__ROLE
    all_roles = await service.get_all_roles(token)
    list_items = [ListItem(i.name, i.id) for i in all_roles]
    keyboard = list_keyboard(token, tag=TAG_CHOOSE_ROLE, pages=[list_items], max_btn_in_row=2, arg=page_index,
                             add_btn_text=None)
    await show(msg, text, is_answer, edited_msg_id, keyboard)
