from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import RoleNotUniqueNameError, NotFoundError, TokenNotValidError
from data.asvttk_service.types import RoleData
from handlers.handlers_delete import show_delete, DeleteItemCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state
from src import commands, strings
from src.states import MainStates, RoleCreateStates, RoleRenameStates
from src.strings import code
from src.utils import get_full_name

router = Router()


class RolesCD(CallbackData, prefix="roles"):
    token: str
    is_create: bool = False
    role_id: Optional[int] = None


class RoleCD(CallbackData, prefix="role"):
    token: str
    role_id: Optional[int] = None
    action: int

    class Action:
        DELETE = 0
        BACK = 1
        RENAME = 2


def roles_keyboard(token: str, items: list[RoleData]):
    kbb = InlineKeyboardBuilder()
    for item in items:
        kbb.add(InlineKeyboardButton(text=item.name, callback_data=RolesCD(token=token, role_id=item.id).pack()))
    kbb.adjust(2)
    kbb.row(InlineKeyboardButton(text=strings.BTN_CREATE, callback_data=RolesCD(token=token, is_create=True).pack()),
            width=1)
    return kbb.as_markup()


def role_keyboard(token: str, role_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    if role_id:
        btn_delete_data = RoleCD(token=token, action=RoleCD.Action.DELETE, role_id=role_id).pack()
        btn_rename_data = RoleCD(token=token, action=RoleCD.Action.RENAME, role_id=role_id).pack()
        kbb.add(InlineKeyboardButton(text=strings.BTN_RENAME, callback_data=btn_rename_data))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data))
    kbb.adjust(2)
    btn_back_data = RoleCD(token=token, action=RoleCD.Action.BACK).pack()
    kbb.row(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data), width=1)
    return kbb.as_markup()


@router.callback_query(RolesCD.filter())
async def roles_callback(callback: CallbackQuery, state: FSMContext):
    data = RolesCD.unpack(callback.data)
    try:
        if data.is_create:
            await service.token_validate(data.token)
            await state.set_state(RoleCreateStates.NAME)
            await state.update_data({"updated_msg_id": callback.message.message_id})
            await callback.message.answer(strings.CREATE_ROLE__ENTER_NAME)
        else:
            await show_role(data.token, data.role_id, callback.message)
            await state.update_data({"updated_msg_id": None})
        await callback.answer()
    except NotFoundError:
        await show_role(data.token, data.role_id, callback.message, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(RoleCD.filter())
async def role_callback(callback: CallbackQuery, state: FSMContext):
    data = RoleCD.unpack(callback.data)
    try:
        if data.action == data.Action.BACK:
            await show_roles(data.token, callback.message, is_answer=False)
            await state.update_data({"updated_msg_id": None})
        if data.action == data.Action.DELETE:
            role = await service.get_role_by_id(data.token, data.role_id)
            text = strings.ROLE_DELETE.format(role_name=role.name)
            await show_delete(data.token, callback.message, deleted_item_id=data.role_id, text=text, tag="role",
                              is_answer=False)
            await state.update_data({"updated_msg_id": None})
        if data.action == data.Action.RENAME:
            role = await service.get_role_by_id(data.token, data.role_id)
            await state.set_state(RoleRenameStates.RENAME)
            await state.update_data({"updated_item_id": role.id})
            await state.update_data({"updated_msg_id": callback.message.message_id})
            await callback.message.answer(strings.ROLE__RENAME.format(role_name=role.name))
        await callback.answer()
    except NotFoundError:
        await show_role(data.token, data.role_id, callback.message, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(DeleteItemCD.filter(F.tag == 'role'))
async def delete_role_callback(callback: CallbackQuery):
    data = DeleteItemCD.unpack(callback.data)
    try:
        if data.is_delete:
            role = await service.get_role_by_id(data.token, data.deleted_item_id)
            await service.delete_role(data.token, data.deleted_item_id)
            await show_roles(data.token, callback.message, is_answer=False)
            await callback.answer(text=strings.ROLE_DELETED.format(role_name=role.name))
        else:
            await show_role(data.token, data.deleted_item_id, callback.message)
            await callback.answer()
    except NotFoundError:
        await callback.answer(text=strings.ROLE__NOT_FOUND)
        await show_roles(data.token, callback.message, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(RoleCreateStates.NAME)
async def create_role_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.CREATE_ROLE__ERROR_FORMAT)
        return
    try:
        role = await service.create_role(token, name=msg.text)
        await msg.answer(strings.CREATE_ROLE__SUCCESS.format(role_name=role.name))
        updated_msg_id: Optional[int] = (await state.get_data()).get("updated_msg_id", None)
        if updated_msg_id:
            await show_roles(token, msg, edited_msg_id=updated_msg_id, is_answer=False)
        await reset_state(state)
    except ValueError:
        await msg.answer(strings.CREATE_ROLE__ENTER_NAME__TOO_LONGER_ERROR)
    except RoleNotUniqueNameError:
        await msg.answer(strings.CREATE_ROLE__ENTER_NAME__UNIQUE_NAME_ERROR)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.message(RoleRenameStates.RENAME)
async def rename_role_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        role_id = (await state.get_data()).get("updated_item_id")
        await service.update_role(token, role_id=role_id, name=msg.text)
        await msg.answer(strings.ROLE__RENAME__SUCCESS)
        updated_msg_id: Optional[int] = (await state.get_data()).get("updated_msg_id", None)
        if updated_msg_id:
            await show_role(token, role_id, msg, edited_msg_id=updated_msg_id, is_answer=False)
        await reset_state(state)
    except ValueError:
        await msg.answer(strings.CREATE_ROLE__ENTER_NAME__TOO_LONGER_ERROR)
    except RoleNotUniqueNameError:
        await msg.answer(strings.CREATE_ROLE__ENTER_NAME__UNIQUE_NAME_ERROR)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except NotFoundError:
        await msg.answer(strings.ROLE__NOT_FOUND)
        await reset_state(state)


@router.message(MainStates.ADMIN, Command(commands.ROLES))
async def roles_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await show_roles(token, msg, is_answer=True)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


async def show_roles(token: str, msg: Message, edited_msg_id: Optional[int] = None, is_answer: bool = True):
    try:
        roles = await service.get_all_roles(token)
        text = strings.ROLES if roles else strings.ROLES__EMPTY
        keyboard = roles_keyboard(token, roles)
        if not is_answer and edited_msg_id:
            await msg.bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=edited_msg_id,
                                            reply_markup=keyboard)
        elif not is_answer and not edited_msg_id:
            await msg.edit_text(text=text, reply_markup=keyboard)
        else:
            await msg.answer(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


async def show_role(token: str, role_id: int, msg: Message = None, edited_msg_id: Optional[int] = None,
                    is_answer: bool = False):
    keyboard = role_keyboard(token)
    text = strings.ROLE__NOT_FOUND
    try:
        role = await service.get_role_by_id(token, role_id)
        employees_list = " | ".join([code(get_full_name(i.first_name, i.last_name, i.patronymic)) for i in role.accounts])
        employees_list = employees_list if employees_list else "-"
        trainings_list = " | ".join([code(i.name) for i in role.trainings])
        trainings_list = trainings_list if trainings_list else "-"
        date_create = datetime.fromtimestamp(role.date_create).strftime(strings.DATE_FORMAT_FULL)
        text = strings.ROLE.format(role_name=role.name, date_create=date_create, employees_list=employees_list,
                                   trainings_list=trainings_list)
        keyboard = role_keyboard(token, role_id=role_id)
        if not is_answer and edited_msg_id:
            try:
                await msg.bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=edited_msg_id,
                                                reply_markup=keyboard)
            except TelegramBadRequest:
                pass
        elif not is_answer and not edited_msg_id:
            await msg.edit_text(text=text, reply_markup=keyboard)
        else:
            await msg.answer(text=text, reply_markup=keyboard)
    except NotFoundError:
        await msg.edit_text(text=text, reply_markup=keyboard)

