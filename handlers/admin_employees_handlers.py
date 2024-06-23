import asyncio
from html import escape
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.exceptions import TokenNotValidError, NotFoundError, \
    UnknownError, AccessError, AccountNotFoundError
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.models import AccountType
from handlers.handlers_confirmation import show_confirmation, ConfirmationCD
from handlers.handlers_list import list_keyboard, get_pages, ListItem, ListCD, get_safe_page_index
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state, \
    unknown_error, unknown_error_for_callback, set_updated_msg, access_error_for_callback, access_error, \
    get_updated_msg, set_updated_item, get_updated_item
from handlers.value_validators import valid_full_name, valid_content_type_msg, ValueNotValidError, valid_email
from src import commands, strings
from src.keyboards import invite_keyboard
from src.states import MainStates, EmployeeCreateStates, EmployeeEditEmailStates, EmployeeEditFullNameStates
from src.strings import code, field
from src.time_utils import get_date_str, DateFormat
from src.utils import get_full_name_by_account, get_access_key_link, show

router = Router()

TAG_EMPLOYEES = "emp"
TAG_EMPLOYEE_ROLES = "e_r"
TAG_EMPLOYEE_ADD_ROLES = "e_a_r"
TAG_DELETE_EMPLOYEE = "e_del"


class EmployeeCD(CallbackData, prefix="emp"):
    token: str
    employee_id: Optional[int] = None
    action: int

    class Action:
        DELETE = 0
        DENY = 1
        ROLES = 2
        EDIT_FN = 3
        EDIT_EMAIL = 4
        BACK = 5


def employee_keyboard(token: str, employee_id: Optional[int] = None):
    kbb = InlineKeyboardBuilder()
    adjust = []
    if employee_id:
        btn_roles_data = EmployeeCD(token=token, employee_id=employee_id, action=EmployeeCD.Action.ROLES)
        btn_edit_email_data = EmployeeCD(token=token, employee_id=employee_id, action=EmployeeCD.Action.EDIT_EMAIL)
        btn_delete_data = EmployeeCD(token=token, employee_id=employee_id, action=EmployeeCD.Action.DELETE)
        btn_edit_full_name_data = EmployeeCD(token=token, employee_id=employee_id, action=EmployeeCD.Action.EDIT_FN)
        kbb.add(InlineKeyboardButton(text=strings.BTN_ROLES, callback_data=btn_roles_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_EMAIL, callback_data=btn_edit_email_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_FULL_NAME, callback_data=btn_edit_full_name_data.pack()))
        kbb.add(InlineKeyboardButton(text=strings.BTN_DELETE, callback_data=btn_delete_data.pack()))
        adjust += [1, 2, 1]
    btn_back_data = EmployeeCD(token=token, action=EmployeeCD.Action.BACK)
    kbb.row(InlineKeyboardButton(text=strings.BTN_BACK, callback_data=btn_back_data.pack()))
    adjust.append(1)
    kbb.adjust(*adjust)
    return kbb.as_markup()


@router.message(MainStates.ADMIN, Command(commands.EMPLOYEES))
async def employees_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        await show_employees(token, msg)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state, canceled=False)


@router.callback_query(ListCD.filter(F.tag == TAG_EMPLOYEES))
async def employees_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.ADD:
            await state.set_state(EmployeeCreateStates.FULL_NAME)
            await callback.message.answer(strings.CREATE_EMPLOYEE)
            await set_updated_msg(state, callback.message.message_id)
        elif data.action == data.Action.COUNTER:
            await show_employees(data.token, callback.message, is_answer=False)
        elif data.action == data.Action.SELECT:
            await show_employee(data.token, data.selected_item_id, callback.message, is_answer=False)
        elif data.action == data.Action.NEXT_PAGE:
            await show_employees(data.token, callback.message, page_index=data.page_index + 1, is_answer=False)
        elif data.action == data.Action.PREVIOUS_PAGE:
            await show_employees(data.token, callback.message, page_index=data.page_index - 1, is_answer=False)
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.message(EmployeeCreateStates.FULL_NAME)
async def create_employee_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        last_name, first_name, patronymic = valid_full_name(msg.text, null_if_empty=True)
        acc_data = await service.create_employee(token, first_name, last_name, patronymic)
        keyboard = invite_keyboard(AccountType.EMPLOYEE, acc_data.access_key)
        await msg.answer(strings.CREATE_EMPLOYEE__SUCCESS.format(
            access_key=acc_data.access_key,
            access_link=get_access_key_link(acc_data.access_key)), reply_markup=keyboard)
        await asyncio.sleep(0.5)
        message_id, args = await get_updated_msg(state)
        await show_employees(token, msg, edited_msg_id=message_id)
        await reset_state(state)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.callback_query(EmployeeCD.filter())
async def employee_callback(callback: CallbackQuery, state: FSMContext):
    data = EmployeeCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.BACK:
            await show_employees(data.token, callback.message, is_answer=False)
        if data.action == data.Action.EDIT_EMAIL:
            await state.set_state(EmployeeEditEmailStates.EDIT_EMAIL)
            await callback.message.answer(strings.EMPLOYEE__EDIT_EMAIL)
            await set_updated_item(state, data.employee_id)
            await set_updated_msg(state, callback.message.message_id)
        elif data.action == data.Action.DELETE:
            employee = await service.get_employee_by_id(data.token, data.employee_id)
            text = strings.EMPLOYEE_DELETE.format(full_name=escape(get_full_name_by_account(employee,
                                                                                            full_patronymic=True)))
            await show_confirmation(data.token, callback.message, item_id=data.employee_id,
                                    text=text, tag=TAG_DELETE_EMPLOYEE, is_answer=False)
        elif data.action == data.Action.ROLES:
            await show_edit_roles(data.token, data.employee_id, callback.message, is_answer=False)
        elif data.action == data.Action.EDIT_FN:
            await state.set_state(EmployeeEditFullNameStates.EDIT_FULL_NAME)
            await callback.message.answer(strings.EMPLOYEE__EDIT_FULL_NAME)
            await set_updated_item(state, data.employee_id)
            await set_updated_msg(state, callback.message.message_id)
        await callback.answer()
    except NotFoundError:
        await show_employee(data.token, data.employee_id, callback.message, is_answer=False)
        await callback.answer()
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_DELETE_EMPLOYEE))
async def delete_employee_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            await service.delete_employee(data.token, employee_id=data.item_id)
            await callback.answer(text=strings.EMPLOYEE__DELETED)
            await show_employees(data.token, callback.message, is_answer=False)
        else:
            await show_employee(data.token, data.item_id, callback.message, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await show_employee(data.token, data.item_id, callback.message, is_answer=False)
        await callback.answer()
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ListCD.filter(F.tag == TAG_EMPLOYEE_ROLES))
async def roles_employee_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    employee_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.SELECT:
            role = await service.get_role_by_id(data.token, role_id=data.selected_item_id)
            await service.remove_role_from_employee(data.token, employee_id=employee_id, role_id=role.id)
            await callback.answer(strings.EMPLOYEE__ROLES__REMOVED.format(role_name=role.name))
            await show_edit_roles(data.token, employee_id, callback.message, is_answer=False)
        elif data.action == data.Action.ADD:
            await show_add_roles(data.token, employee_id, callback.message, is_answer=False)
        elif data.action == data.Action.BACK:
            await show_employee(data.token, employee_id, callback.message, is_answer=False)
        await callback.answer()
    except NotFoundError:
        await show_edit_roles(data.token, employee_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ListCD.filter(F.tag == TAG_EMPLOYEE_ADD_ROLES))
async def add_roles_employee_callback(callback: CallbackQuery, state: FSMContext):
    data = ListCD.unpack(callback.data)
    employee_id = int(data.arg)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.SELECT:
            role = await service.get_role_by_id(data.token, role_id=data.selected_item_id)
            try:
                await service.add_role_to_employee(data.token, employee_id=employee_id, role_id=role.id)
            except AccountNotFoundError:
                raise NotFoundError()
            await callback.answer(strings.EMPLOYEE__ROLES__ADDED.format(role_name=role.name))
            await show_edit_roles(data.token, employee_id, callback.message, is_answer=False)
        elif data.action == data.Action.BACK:
            await show_edit_roles(data.token, employee_id, callback.message, is_answer=False)
            await callback.answer()
    except NotFoundError:
        await show_add_roles(data.token, employee_id, callback.message, is_answer=False)
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.message(EmployeeEditEmailStates.EDIT_EMAIL)
async def edit_email_employee_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        email = valid_email(msg.text)
        employee_id, args = await get_updated_item(state)
        await service.update_email_employee(token, employee_id, email=email)
        await msg.answer(strings.EMPLOYEE__EDIT_EMAIL__SUCCESS)
        msg_id, args = await get_updated_msg(state)
        await show_employee(token, employee_id, msg, edited_msg_id=msg_id)
        await reset_state(state)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except NotFoundError:
        await msg.answer(text=strings.EMPLOYEE__NOT_FOUND)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.message(EmployeeEditFullNameStates.EDIT_FULL_NAME)
async def edit_full_name_employee_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        last_name, first_name, patronymic = valid_full_name(msg.text)
        employee_id, args = await get_updated_item(state)
        await service.update_full_name_employee(token, employee_id, first_name=first_name, last_name=last_name,
                                                patronymic=patronymic)
        await msg.answer(strings.EMPLOYEE__FULL_NAME__SUCCESS)
        msg_id, args = await get_updated_msg(state)
        await show_employee(token, employee_id, msg, edited_msg_id=msg_id)
        await reset_state(state)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except NotFoundError:
        await msg.answer(text=strings.EMPLOYEE__NOT_FOUND)
        await reset_state(state)
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


async def show_employees(token: str, msg: Message, page_index: int = 0, edited_msg_id: Optional[int] = None,
                         is_answer: bool = True):
    try:
        employees = await service.get_all_employees(token)
        text = strings.EMPLOYEES__EMPTY
        list_items = [ListItem(str(i + 1), employees[i].id, employees[i]) for i in range(len(employees))]
        pages = get_pages(list_items)
        page_index = get_safe_page_index(page_index, len(pages))
        keyboard = list_keyboard(token=token, tag=TAG_EMPLOYEES, pages=pages, page_index=page_index)
        page_items = pages[page_index]
        if page_items:
            items = []
            for item in page_items:
                full_name = get_full_name_by_account(item.obj)
                roles = ", ".join([escape(i.name) for i in item.obj.roles])
                if not roles:
                    roles = strings.EMPLOYEES_ITEM__ROLES_EMPTY
                items.append(strings.EMPLOYEES_ITEM.format(index=item.name, full_name=escape(full_name), roles=roles))
            text = strings.EMPLOYEES.format(items="\n\n".join(items))
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        text = strings.ERROR__ACCESS
        await show(msg, text, is_answer, edited_msg_id)


async def show_employee(token: str, employee_id: int, msg: Message, edited_msg_id: Optional[int] = None,
                        is_answer: bool = True):
    text = strings.EMPLOYEE__NOT_FOUND
    keyboard = employee_keyboard(token)
    try:
        employee = await service.get_employee_by_id(token, employee_id)
        keyboard = employee_keyboard(token, employee_id)
        roles_list = " | ".join([code(escape(i.name)) for i in employee.roles])
        text = strings.EMPLOYEE.format(
            date_create=get_date_str(employee.date_create, time_format=DateFormat.FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE),
            last_name=escape(field(employee.last_name)), first_name=escape(field(employee.first_name)),
            patronymic=escape(field(employee.patronymic)), email=escape(field(employee.email)),
            roles_list=roles_list if roles_list else strings.EMPLOYEES_ITEM__ROLES_EMPTY,
        )
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except AccessError:
        text = strings.ERROR__ACCESS
        await show(msg, text, is_answer, edited_msg_id, keyboard)
    except NotFoundError:
        await show(msg, text, is_answer, edited_msg_id, keyboard)


async def show_edit_roles(token: str, employee_id: int, msg: Message, page_index: Optional[int] = 0,
                          is_answer: bool = True):
    try:
        employee = await service.get_employee_by_id(token, employee_id)
        roles = employee.roles
        list_items = [ListItem(i.name, i.id) for i in roles]
        keyboard = list_keyboard(token, tag=TAG_EMPLOYEE_ROLES, pages=[list_items], max_btn_in_row=2,
                                 arg=employee_id, arg1=page_index, back_btn_text=strings.BTN_BACK)
        text = strings.EMPLOYEE__ROLES.format(
            full_name=escape(get_full_name_by_account(employee, full_patronymic=True)))
        await show(msg, text, is_answer, keyboard=keyboard)
    except AccessError:
        await show_employee(token, employee_id, msg, is_answer=False)
    except NotFoundError:
        await show_employee(token, employee_id, msg, is_answer=False)


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
    except AccessError:
        await show_employee(token, employee_id, msg, is_answer=False)
    except NotFoundError:
        await show_employee(token, employee_id, msg, is_answer=False)
