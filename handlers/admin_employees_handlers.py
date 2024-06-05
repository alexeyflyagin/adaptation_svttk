from typing import Optional

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.token import validate_token

from data.asvttk_service.exceptions import TokenNotValidError, EmailValueError, InitialsValueError
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.types import EmployeeData
from handlers.handlers_list import list_keyboard, get_pages, ListItem, get_items_by_page, ListCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, reset_state
from src import commands, strings
from src.states import MainStates, CreateEmployeeStates
from src.utils import get_full_name, get_full_name_by_account, cut_text, key_link

router = Router()


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
        await state.update_data({"updated_msg_id": None})
        if data.action == data.Action.ADD:
            await state.set_state(CreateEmployeeStates.FULL_NAME)
            await callback.message.answer(strings.CREATE_EMPLOYEE)
            await state.update_data({"updated_msg_id": callback.message.message_id})
        elif data.action == data.Action.COUNTER:
            print("COUNTER")
        elif data.action == data.Action.SELECT:
            print("SELECT")
        elif data.action == data.Action.NEXT_PAGE:
            print("NEXT_PAGE")
        elif data.action == data.Action.PREVIOUS_PAGE:
            print("PREVIOUS_PAGE")
        await callback.answer()
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback)


@router.message(CreateEmployeeStates.FULL_NAME)
async def create_employee_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    if msg.content_type != ContentType.TEXT:
        await msg.answer(strings.CREATE_EMPLOYEE__ERROR_FORMAT)
        return
    try:
        initials = [i.replace(" ", "") for i in msg.text.split()]
        if len(initials) != 3:
            raise InitialsValueError()
        initials = [None if i == "-" else i for i in msg.text.split()]
        acc_data = await service.create_employee(token, first_name=initials[1], last_name=initials[0],
                                                 patronymic=initials[2])
        await msg.answer(strings.CREATE_EMPLOYEE__SUCCESS.format(access_key=acc_data.access_key,
                                                                 access_link=key_link(acc_data.access_key)))
        updated_msg_id: Optional[int] = (await state.get_data()).get("updated_msg_id", None)
        if updated_msg_id:
            await show_employees(token, msg, edited_msg_id=updated_msg_id, is_answer=False)
        await reset_state(state)
    except InitialsValueError:
        await msg.answer(strings.CREATE_EMPLOYEE__ERROR_FORMAT)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


async def show_employees(token: str, msg: Message, page_index: int = 0, edited_msg_id: Optional[int] = None,
                         is_answer: bool = True):
    try:
        employees = await service.get_all_employees(token)
        text = strings.EMPLOYEES__EMPTY
        list_items = [ListItem(str(i + 1), employees[i].id) for i in range(len(employees))]
        pages = get_pages(list_items)
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
