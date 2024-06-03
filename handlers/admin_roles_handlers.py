from datetime import datetime
from enum import Enum
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import RoleNotUniqueNameError, NotFoundError
from data.asvttk_service.types import RoleData
from handlers import general
from src import commands, strings
from src.states import MainStates, CreateRoleStates
from src.utils import get_token, get_full_name

router = Router()


class RolesCD(CallbackData, prefix="roles"):
    token: str
    is_create: bool = False
    role_id: Optional[int] = None


class RoleCD(CallbackData, prefix="role"):
    token: str
    role_id: Optional[int] = None
    action: str

    class Action:
        DELETE = "delete"
        BACK = "back"


def roles_keyboard(token: str, items: list[RoleData]):
    kbb = InlineKeyboardBuilder()
    for item in items:
        kbb.add(InlineKeyboardButton(text=item.name, callback_data=RolesCD(token=token, role_id=item.id).pack()))
    kbb.adjust(2)
    kbb.row(InlineKeyboardButton(text=strings.BTN_ADD, callback_data=RolesCD(token=token, is_create=True).pack()),
            width=1)
    return kbb.as_markup()


def role_keyboard(token: str, role_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    if role_id:
        btn_delete_data = RoleCD(token=token, action=RoleCD.Action.DELETE, role_id=role_id).pack()
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data))
    kbb.adjust(1)
    btn_back_data = RoleCD(token=token, action=RoleCD.Action.BACK).pack()
    kbb.row(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data), width=1)
    return kbb.as_markup()


@router.callback_query(MainStates.ADMIN, RolesCD.filter())
async def roles_callback(callback: CallbackQuery, state: FSMContext):
    token = await get_token(state)
    data = RolesCD.unpack(callback.data)
    if token != data.token:
        await callback.answer(strings.SESSION_ERROR)
        await callback.message.edit_reply_markup(inline_message_id=None)
        return
    if data.is_create:
        await state.set_state(CreateRoleStates.NAME)
        await callback.message.answer(strings.CREATE_ROLE__ENTER_NAME)
    else:
        await show_role(data.role_id, callback.message, state)
    await callback.answer()


@router.callback_query(MainStates.ADMIN, RoleCD.filter())
async def role_callback(callback: CallbackQuery, state: FSMContext):
    token = await get_token(state)
    data = RoleCD.unpack(callback.data)
    if token != data.token:
        await callback.answer(strings.SESSION_ERROR)
        await callback.message.edit_reply_markup(inline_message_id=None)
        return
    if data.action == data.Action.BACK:
        await show_roles(callback.message, state, is_answer=False)
    await callback.answer()


@router.message(CreateRoleStates.NAME)
async def create_role_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        role = await service.create_role(token, name=msg.text)
        await msg.answer(strings.CREATE_ROLE__SUCCESS.format(role_name=role.name))
        await general.to_main_state(msg, state)
    except ValueError:
        await msg.answer(strings.CREATE_ROLE__ENTER_NAME__TOO_LONGER_ERROR)
    except RoleNotUniqueNameError:
        await msg.answer(strings.CREATE_ROLE__ENTER_NAME__UNIQUE_NAME_ERROR)


@router.message(MainStates.ADMIN, Command(commands.ROLES))
async def roles_handler(msg: Message, state: FSMContext):
    await show_roles(msg, state, is_answer=True)


async def show_roles(msg: Message, state: FSMContext, is_answer: bool = True):
    token = await get_token(state)
    roles = await service.get_all_roles(token)
    text = strings.ROLES if roles else strings.ROLES__EMPTY
    keyboard = roles_keyboard(token, roles)
    if is_answer:
        await msg.answer(text=text, reply_markup=keyboard)
    else:
        await msg.edit_text(text=text, reply_markup=keyboard)


async def show_role(role_id: int, msg: Message, state: FSMContext):
    token = await get_token(state)
    keyboard = role_keyboard(token)
    text = strings.ROLE__NOT_FOUND
    try:
        role = await service.get_role_by_id(token, role_id)
        employees_list = ", ".join([get_full_name(i.first_name, i.last_name, i.patronymic) for i in role.accounts])
        employees_list = employees_list if employees_list else "-"
        trainings_list = ", ".join([i.name for i in role.trainings])
        trainings_list = trainings_list if trainings_list else "-"
        date_create = datetime.fromtimestamp(role.date_create).strftime(strings.DATE_FORMAT_FULL)
        text = strings.ROLE.format(role_name=role.name, date_create=date_create, employees_list=employees_list,
                                   trainings_list=trainings_list)
        keyboard = role_keyboard(token, role_id=role_id)
    except NotFoundError:
        pass
    await msg.edit_text(text=text, reply_markup=keyboard)
