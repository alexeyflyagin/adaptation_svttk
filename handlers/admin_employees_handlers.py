from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, SwitchInlineQueryChosenChat
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.exceptions import TokenNotValidError, InitialsValueError, NotFoundError, EmailValueError
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.types import EmployeeData
from handlers.handlers_delete import show_delete, DeleteItemCD
from handlers.handlers_list import list_keyboard, get_pages, ListItem, get_items_by_page, ListCD, get_safe_page_index
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state
from src import commands, strings
from src.states import MainStates, EmployeeCreateStates, EmployeeEditEmailStates, EmployeeEditFullNameStates
from src.strings import code
from src.utils import get_full_name_by_account, get_access_key_link, show

router = Router()

TAG_EMPLOYEE_ROLES = "emp_roles"
TAG_EMPLOYEE_ADD_ROLES = "emp_add_roles"


class EmployeeCD(CallbackData, prefix="employee"):
    token: str
    page_index: int = 0
    employee_id: Optional[int] = None
    action: int

    class Action:
        DELETE = 0
        DENY = 1
        ROLES = 2
        EDIT_FN = 3
        EDIT_EMAIL = 4
        BACK = 5


def employee_keyboard(token: str, page_index: int, employee_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if employee_id:
        btn_roles_data = EmployeeCD(token=token, page_index=page_index, employee_id=employee_id,
                                    action=EmployeeCD.Action.ROLES)
        btn_edit_email_data = EmployeeCD(token=token, page_index=page_index, employee_id=employee_id,
                                         action=EmployeeCD.Action.EDIT_EMAIL)
        btn_delete_data = EmployeeCD(token=token, page_index=page_index, employee_id=employee_id,
                                     action=EmployeeCD.Action.DELETE)
        btn_edit_full_name_data = EmployeeCD(token=token, page_index=page_index, employee_id=employee_id,
                                             action=EmployeeCD.Action.EDIT_FN)
        kbb.add(InlineKeyboardButton(text=strings.BTN_ROLES, callback_data=btn_roles_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_EMAIL, callback_data=btn_edit_email_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_FULL_NAME, callback_data=btn_edit_full_name_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [1, 2, 1]
    btn_back_data = EmployeeCD(token=token, page_index=page_index, action=EmployeeCD.Action.BACK)
    kbb.row(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


def invite_keyboard(first_name: str, access_key: str):
    kbb = InlineKeyboardBuilder()
    text = strings.EMPLOYEE_INVITE.format(first_name=first_name, invite_link=get_access_key_link(access_key))
    query = SwitchInlineQueryChosenChat(query=text, allow_user_chats=True)
    kbb.row(InlineKeyboardButton(text=strings.BTN_INVITE, switch_inline_query_chosen_chat=query), width=1)
    return kbb.as_markup()


@router.message(MainStates.ADMIN, Command(commands.EMPLOYEES))
async def employees_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await show_employees(token, msg)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(ListCD.filter(F.tag == "employees"))
async def list_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        await state.update_data({"updated_msg": None})
        if data.action == data.Action.ADD:
            await state.set_state(EmployeeCreateStates.FULL_NAME)
            await callback.message.answer(strings.CREATE_EMPLOYEE)
            await state.update_data({"updated_msg": [callback.message.message_id, data.page_index]})
        elif data.action == data.Action.COUNTER:
            await show_employees(data.token, callback.message, page_index=data.page_index, is_answer=False)
        elif data.action == data.Action.SELECT:
            await show_employee(data.token, data.selected_item_id, callback.message, page_index=data.page_index,
                                is_answer=False)
        elif data.action == data.Action.NEXT_PAGE:
            await show_employees(data.token, callback.message, page_index=data.page_index + 1, is_answer=False)
        elif data.action == data.Action.PREVIOUS_PAGE:
            await show_employees(data.token, callback.message, page_index=data.page_index - 1, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


def get_initials_from_text(text: str) -> list[str]:
    initials = [i.replace(" ", "") for i in text.split()]
    if len(initials) != 3 or initials[1] == '-':
        raise InitialsValueError()
    return initials


@router.message(EmployeeCreateStates.FULL_NAME)
async def create_employee_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.CREATE_EMPLOYEE__ERROR_FORMAT)
        return
    try:
        initials = get_initials_from_text(msg.text)
        acc_data = await service.create_employee(token, first_name=initials[1], last_name=initials[0],
                                                 patronymic=initials[2])
        account = await service.get_employee_by_id(token, acc_data.account_id)
        keyboard = invite_keyboard(account.first_name, acc_data.access_key)
        await msg.answer(strings.CREATE_EMPLOYEE__SUCCESS.format(
            access_key=acc_data.access_key,
            access_link=get_access_key_link(acc_data.access_key)), reply_markup=keyboard)
        updated_msg: Optional[list] = (await state.get_data()).get("updated_msg", None)
        if updated_msg:
            await show_employees(token, msg, edited_msg_id=updated_msg[0], page_index=updated_msg[1], is_answer=False)
        await reset_state(state)
    except InitialsValueError:
        await msg.answer(strings.CREATE_EMPLOYEE__ERROR_FORMAT)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.callback_query(EmployeeCD.filter())
async def employee_callback(callback: CallbackQuery, state: FSMContext):
    data = EmployeeCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        await state.update_data({"update_msg": None})
        if data.action == data.Action.BACK:
            await show_employees(data.token, callback.message, page_index=data.page_index, is_answer=False)
        if data.action == data.Action.EDIT_EMAIL:
            await state.set_state(EmployeeEditEmailStates.EditEmail)
            await callback.message.answer(strings.EMPLOYEE__EDIT_EMAIL)
            await state.update_data({"updated_item_id": data.employee_id})
            await state.update_data({"update_msg": [callback.message.message_id, data.page_index]})
        elif data.action == data.Action.DELETE:
            employee = await service.get_employee_by_id(data.token, data.employee_id)
            text = strings.EMPLOYEE_DELETE.format(full_name=get_full_name_by_account(employee, full_patronymic=True))
            await show_delete(data.token, callback.message, args=data.page_index, deleted_item_id=data.employee_id,
                              text=text, tag="employee", is_answer=False)
        elif data.action == data.Action.ROLES:
            await show_edit_roles(data.token, data.employee_id, callback.message, is_answer=False)
        elif data.action == data.Action.EDIT_FN:
            await state.set_state(EmployeeEditFullNameStates.EditFullName)
            await callback.message.answer(strings.EMPLOYEE__EDIT_FULL_NAME)
            await state.update_data({"updated_item_id": data.employee_id})
            await state.update_data({"update_msg": [callback.message.message_id, data.page_index]})
        await callback.answer()
    except NotFoundError:
        await show_employee(data.token, data.employee_id, callback.message, page_index=data.page_index, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(DeleteItemCD.filter(F.tag == "employee"))
async def delete_employee_callback(callback: CallbackQuery):
    data = DeleteItemCD.unpack(callback.data)
    page_index = int(data.args)
    try:
        await service.token_validate(data.token)
        if data.is_delete:
            await service.delete_employee(data.token, employee_id=data.deleted_item_id)
            await callback.answer(text=strings.EMPLOYEE__DELETED)
            await show_employees(data.token, callback.message, page_index=page_index, is_answer=False)
        else:
            await show_employee(data.token, data.deleted_item_id, callback.message, page_index=page_index,
                                is_answer=False)
            await callback.answer()
    except NotFoundError:
        await callback.answer(text=strings.EMPLOYEE__NOT_FOUND)
        await show_employees(data.token, data.callback.message, page_index=page_index, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(ListCD.filter(F.tag == TAG_EMPLOYEE_ROLES))
async def roles_employee_callback(callback: CallbackQuery):
    data = ListCD.unpack(callback.data)
    employee_id = int(data.arg)
    page_index = int(data.arg1)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.SELECT:
            role = await service.get_role_by_id(data.token, role_id=data.selected_item_id)
            await service.remove_role_from_employee(data.token, employee_id=employee_id, role_id=role.id)
            await callback.answer(strings.EMPLOYEE__ROLES__REMOVED.format(role_name=role.name))
            await show_edit_roles(data.token, employee_id, callback.message, is_answer=False)
        elif data.action == data.Action.ADD:
            await show_add_roles(data.token, employee_id, callback.message, page_index=data.page_index, is_answer=False)
            await callback.answer()
        elif data.action == data.Action.BACK:
            await show_employee(data.token, employee_id, callback.message, page_index=page_index, is_answer=False)
    except NotFoundError:
        await callback.answer(text=strings.ROLE__NOT_FOUND)
        await show(callback.message, strings.ROLE__NOT_FOUND, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.callback_query(ListCD.filter(F.tag == TAG_EMPLOYEE_ADD_ROLES))
async def add_roles_employee_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    employee_id = int(data.arg)
    page_index = int(data.arg1)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.SELECT:
            role = await service.get_role_by_id(data.token, role_id=data.selected_item_id)
            await service.add_role_to_employee(data.token, employee_id=employee_id, role_id=role.id)
            state_data = await state.get_data()
            update_msg = state_data.get("update_msg")
            if update_msg:
                await show_employee(data.token, employee_id, callback.message, update_msg[1],
                                    edited_msg_id=update_msg[0], is_answer=False)
            await callback.answer(strings.EMPLOYEE__ROLES__ADDED.format(role_name=role.name))
            await show_edit_roles(data.token, employee_id, callback.message, is_answer=False)
        elif data.action == data.Action.BACK:
            await show_edit_roles(data.token, employee_id, callback.message, page_index=page_index, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await callback.answer(text=strings.ROLE__NOT_FOUND)
        await show(callback.message, strings.ROLE__NOT_FOUND, is_answer=False)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(EmployeeEditEmailStates.EditEmail)
async def edit_email_employee_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        state_data = await state.get_data()
        employee_id = state_data.get("updated_item_id")
        update_msg = state_data.get("update_msg")
        await service.update_email_employee(token, employee_id, email=msg.text)
        await msg.answer(strings.EMPLOYEE__EDIT_EMAIL__SUCCESS)
        if update_msg:
            await show_employee(token, employee_id, msg, update_msg[1], update_msg[0], is_answer=False)
        await reset_state(state)
    except NotFoundError:
        await msg.answer(text=strings.EMPLOYEE__NOT_FOUND)
        await reset_state(state)
    except EmailValueError:
        await msg.answer(strings.EMPLOYEE__EDIT_EMAIL__EMAIL_ERROR)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.message(EmployeeEditFullNameStates.EditFullName)
async def edit_full_name_employee_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.CREATE_EMPLOYEE__ERROR_FORMAT)
        return
    try:
        initials = get_initials_from_text(msg.text)
        state_data = await state.get_data()
        employee_id = state_data.get("updated_item_id")
        update_msg = state_data.get("update_msg")
        await service.update_full_name_employee(token, employee_id, first_name=initials[1], last_name=initials[0],
                                                patronymic=initials[2])
        await msg.answer(strings.EMPLOYEE__FULL_NAME__SUCCESS)
        if update_msg:
            await show_employee(token, employee_id, msg, update_msg[1], update_msg[0], is_answer=False)
        await reset_state(state)
    except InitialsValueError:
        await msg.answer(strings.CREATE_EMPLOYEE__ERROR_FORMAT)
    except NotFoundError:
        await msg.answer(text=strings.EMPLOYEE__NOT_FOUND)
        await reset_state(state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


async def show_employees(token: str, msg: Message, page_index: int = 0, edited_msg_id: Optional[int] = None,
                         is_answer: bool = True):
    try:
        employees = await service.get_all_employees(token)
        text = strings.EMPLOYEES__EMPTY
        list_items = [ListItem(str(i + 1), employees[i].id) for i in range(len(employees))]
        pages = get_pages(list_items)
        page_index = get_safe_page_index(page_index, len(pages))
        keyboard = list_keyboard(token=token, tag="employees", pages=pages, page_index=page_index)
        page_employees: list[EmployeeData] = get_items_by_page(employees, pages, page_index)
        page_items = pages[page_index]
        if page_employees:
            items = []
            for i in range(len(page_employees)):
                page_item = page_items[i]
                page_employee = page_employees[i]
                full_name = get_full_name_by_account(page_employee)
                roles = ", ".join([i.name for i in page_employee.roles])
                if not roles:
                    roles = strings.EMPLOYEES_ITEM__ROLES_EMPTY
                items.append(strings.EMPLOYEES_ITEM.format(index=page_item.name, full_name=full_name, roles=roles))
            text = strings.EMPLOYEES.format(items="\n\n".join(items))
        if not is_answer and edited_msg_id:
            await msg.bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=edited_msg_id,
                                            reply_markup=keyboard)
        elif not is_answer and not edited_msg_id:
            await msg.edit_text(text=text, reply_markup=keyboard)
        else:
            await msg.answer(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


async def show_employee(token: str, employee_id: int, msg: Message, page_index: int = 0,
                        edited_msg_id: Optional[int] = None, is_answer: bool = True):
    text = strings.EMPLOYEE__NOT_FOUND
    keyboard = employee_keyboard(token, page_index)
    try:
        employee = await service.get_employee_by_id(token, employee_id)
        keyboard = employee_keyboard(token, page_index, employee_id)
        roles_list = " | ".join([code(i.name) for i in employee.roles])
        text = strings.EMPLOYEE.format(
            date_create=datetime.fromtimestamp(employee.date_create).strftime(strings.DATE_FORMAT_FULL),
            last_name=employee.last_name if employee.last_name else strings.EMPTY_FIELD,
            first_name=employee.first_name if employee.first_name else strings.EMPTY_FIELD,
            patronymic=employee.patronymic if employee.patronymic else strings.EMPTY_FIELD,
            email=employee.email if employee.email else strings.EMPTY_FIELD,
            roles_list=roles_list if roles_list else strings.EMPLOYEES_ITEM__ROLES_EMPTY,
        )
        if not is_answer and edited_msg_id:
            await msg.bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=edited_msg_id,
                                            reply_markup=keyboard)
        elif not is_answer and not edited_msg_id:
            await msg.edit_text(text=text, reply_markup=keyboard)
        else:
            await msg.answer(text=text, reply_markup=keyboard)
    except NotFoundError:
        await msg.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


async def show_edit_roles(token: str, employee_id: int, msg: Message, page_index: Optional[int] = 0,
                          is_answer: bool = True):
    try:
        employee = await service.get_employee_by_id(token, employee_id)
        roles = employee.roles
        list_items = [ListItem(i.name, i.id) for i in roles]
        keyboard = list_keyboard(token, tag=TAG_EMPLOYEE_ROLES, pages=[list_items], max_btn_in_row=2,
                                 arg=employee_id, arg1=page_index, back_btn_text=strings.BTN_BACK)
        text = strings.EMPLOYEE__ROLES.format(full_name=get_full_name_by_account(employee, full_patronymic=True))
        await show(msg, text, is_answer, keyboard=keyboard)
    except NotFoundError:
        await show(msg, strings.EMPLOYEE__NOT_FOUND, is_answer=True)


async def show_add_roles(token: str, employee_id: int, msg: Message, page_index: Optional[int] = 0,
                         is_answer: bool = True):
    try:
        text = strings.EMPLOYEE__ALL_ROLES__FULL
        all_roles = await service.get_all_roles(token)
        employee = await service.get_employee_by_id(token, employee_id)
        exist_role_ids = [i.id for i in employee.roles]
        roles = [i for i in all_roles if i.id not in exist_role_ids]
        list_items = [ListItem(i.name, i.id) for i in roles]
        keyboard = list_keyboard(token, tag=TAG_EMPLOYEE_ADD_ROLES, pages=[list_items], max_btn_in_row=2,
                                 arg=employee_id, arg1=page_index, add_btn_text=None, back_btn_text=strings.BTN_BACK)
        if roles:
            text = strings.EMPLOYEE__ALL_ROLES
        elif not all_roles:
            text = strings.EMPLOYEE__ALL_ROLES__NOT_FOUND
        await show(msg, text, is_answer, keyboard=keyboard)
    except NotFoundError:
        await show(msg, strings.EMPLOYEE__NOT_FOUND, is_answer=True)
