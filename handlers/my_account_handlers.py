import asyncio
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service.exceptions import TokenNotValidError, AccessError, UnknownError, NotFoundError
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.models import AccountType
from data.asvttk_service.types import AccountData, EmployeeData
from handlers.authorization_handlers import show_log_out_warning
from handlers.handlers_confirmation import show_confirmation, ConfirmationCD
from handlers.handlers_utils import get_token, token_not_valid_error, token_not_valid_error_for_callback, delete_msg, \
    unknown_error, unknown_error_for_callback, log_out, access_error_for_callback, set_updated_item, set_updated_msg, \
    get_updated_item, get_updated_msg, reset_state, access_error
from handlers.value_validators import valid_content_type_msg, valid_email, ValueNotValidError, valid_full_name
from src import commands, strings
from src.keyboards import invite_keyboard
from src.states import MainStates, MyAccountEditStates
from src.strings import field, code, italic, eschtml, item_id
from src.utils import get_account_type_str, show, get_access_key_link

router = Router()

TAG_LOG_IN_DATA_INSTRUCTION = "lid_info"
TAG_GIVE_UP_WARNING = "gu_warn"


class MyAccountCD(CallbackData, prefix="my_account"):
    token: str
    action: int

    class Action:
        EDIT_EMAIL = 0
        LOG_IN_DATA = 1
        LOG_IN_DATA__READ_IT = 2
        LOG_OUT = 3
        GIVE_UP = 4
        EDIT_FN = 5


def get_log_in_data_keyboard(access_key: str):
    kbb = InlineKeyboardBuilder()
    adjust = []
    url = get_access_key_link(access_key=access_key)
    kbb.add(InlineKeyboardButton(text=strings.BTN_LOG_IN, url=url))
    adjust += [1]
    kbb.adjust(*adjust)
    return kbb.as_markup()


def log_in_data_instruction_keyboard(token: str) -> InlineKeyboardMarkup:
    kbb = InlineKeyboardBuilder()
    btn_read_it_data = MyAccountCD(token=token, action=MyAccountCD.Action.LOG_IN_DATA__READ_IT)
    kbb.add(InlineKeyboardButton(text=strings.BTN_READ_IT, callback_data=btn_read_it_data.pack()))
    return kbb.as_markup()


def my_account_keyboard(token: str, account_type: AccountType) -> InlineKeyboardMarkup:
    kbb = InlineKeyboardBuilder()
    adjust = []
    btn_access_key_data = MyAccountCD(token=token, action=MyAccountCD.Action.LOG_IN_DATA)
    kbb.add(InlineKeyboardButton(text=strings.BTN_ACCESS_KEY, callback_data=btn_access_key_data.pack()))
    adjust += [1]
    if account_type == AccountType.ADMIN:
        btn_edit_email_data = MyAccountCD(token=token, action=MyAccountCD.Action.EDIT_EMAIL)
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_EMAIL, callback_data=btn_edit_email_data.pack()))
        btn_edit_fn_data = MyAccountCD(token=token, action=MyAccountCD.Action.EDIT_FN)
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_FULL_NAME, callback_data=btn_edit_fn_data.pack()))
        btn_give_up_data = MyAccountCD(token=token, action=MyAccountCD.Action.GIVE_UP)
        kbb.add(InlineKeyboardButton(text=strings.BTN_GIVE_UP_ACCOUNT, callback_data=btn_give_up_data.pack()))
        adjust += [2, 1]
    elif account_type == AccountType.EMPLOYEE:
        btn_edit_email_data = MyAccountCD(token=token, action=MyAccountCD.Action.EDIT_EMAIL)
        kbb.add(InlineKeyboardButton(text=strings.BTN_EDIT_EMAIL, callback_data=btn_edit_email_data.pack()))
        adjust += [1]
    btn_log_out_data = MyAccountCD(token=token, action=MyAccountCD.Action.LOG_OUT)
    kbb.add(InlineKeyboardButton(text=strings.BTN_LOG_OUT, callback_data=btn_log_out_data.pack()))
    kbb.adjust(*adjust)
    return kbb.as_markup()


@router.message(MainStates.ADMIN, Command(commands.MYACCOUNT))
@router.message(MainStates.EMPLOYEE, Command(commands.MYACCOUNT))
async def my_account_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        await show_my_account(token, msg)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state, canceled=False)


@router.callback_query(MyAccountCD.filter())
async def my_account_callback(callback: CallbackQuery, state: FSMContext):
    data = MyAccountCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        try:
            account = await service.get_account_by_token(data.token)
        except NotFoundError:
            raise TokenNotValidError()
        if data.action == data.Action.LOG_IN_DATA:
            keyboard = log_in_data_instruction_keyboard(data.token)
            await callback.message.edit_text(text=strings.LOG_IN_DATA__INSTRUCTION, reply_markup=keyboard)
            await callback.answer()
        elif data.action == data.Action.LOG_IN_DATA__READ_IT:
            await show_my_account(data.token, callback.message, is_answer=False)
            await callback.answer()
            await show_log_in_data(data.token, callback.message)
        elif data.action == data.Action.GIVE_UP:
            text = strings.GIVE_UP_ACCOUNT_WARNING
            await show_confirmation(data.token, callback.message, 0, text=text,
                                    tag=TAG_GIVE_UP_WARNING, is_answer=False)
            await callback.answer()
        elif data.action == data.Action.EDIT_EMAIL:
            text = strings.EDIT_EMAIL
            await set_updated_item(state, account.id)
            await set_updated_msg(state, callback.message.message_id)
            await state.set_state(MyAccountEditStates.EMAIL)
            await callback.message.answer(text)
            await callback.answer()
        elif data.action == data.Action.EDIT_FN:
            text = strings.EDIT_FULL_NAME
            await set_updated_item(state, account.id)
            await set_updated_msg(state, callback.message.message_id)
            await state.set_state(MyAccountEditStates.FULL_NAME)
            await callback.message.answer(text)
            await callback.answer()
        elif data.action == data.Action.LOG_OUT:
            text = strings.LOG_OUT__WARNING
            await show_log_out_warning(data.token, callback.message, warning_text=text)
            await callback.answer()
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.callback_query(ConfirmationCD.filter(F.tag == TAG_GIVE_UP_WARNING))
async def give_up_callback(callback: CallbackQuery, state: FSMContext):
    data = ConfirmationCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.is_agree:
            give_up_data = await service.give_up_account(data.token)
            await callback.answer()
            await log_out(callback.message, state)
            invite_link = get_access_key_link(give_up_data.invite_access_key)
            text = strings.EMPLOYEE_INVITE_LETTER.format(invite_link=invite_link)
            keyboard = invite_keyboard(AccountType.ADMIN, give_up_data.invite_access_key)
            await show(callback.message, text, is_answer=True, keyboard=keyboard)
        else:
            await show_my_account(data.token, callback.message, is_answer=False)
            await callback.answer()
    except AccessError:
        await access_error_for_callback(callback, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)
    except UnknownError:
        await unknown_error_for_callback(callback, state)


@router.message(MyAccountEditStates.EMAIL)
async def edit_my_email_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        email = valid_email(msg.text)
        account_id, args = await get_updated_item(state)
        try:
            await service.update_email_account(token, account_id, email=email)
        except NotFoundError:
            raise TokenNotValidError()
        await msg.answer(strings.EDIT_EMAIL__SUCCESS)
        await reset_state(state)
        msg_id, args = await get_updated_msg(state)
        await show_my_account(token, msg, edited_msg_id=msg_id)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


@router.message(MyAccountEditStates.FULL_NAME)
async def edit_my_full_name_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    try:
        await service.token_validate(token)
        valid_content_type_msg(msg, ContentType.TEXT)
        last_name, first_name, patronymic = valid_full_name(msg.text)
        account_id, args = await get_updated_item(state)
        try:
            await service.update_full_name_account(token, account_id, first_name=first_name, last_name=last_name,
                                                   patronymic=patronymic)
        except NotFoundError:
            raise TokenNotValidError()
        await msg.answer(strings.EDIT_FULL_NAME__SUCCESS)
        msg_id, args = await get_updated_msg(state)
        await show_my_account(token, msg, edited_msg_id=msg_id)
        await reset_state(state)
    except ValueNotValidError as e:
        await msg.answer(strings.error_value(e.error_msg))
    except AccessError:
        await access_error(msg, state)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)
    except UnknownError:
        await unknown_error(msg, state)


async def show_my_account(token: str, msg: Message, edited_msg_id: Optional[int] = None, is_answer: bool = True):
    try:
        account: AccountData | EmployeeData
        account = await service.get_account_by_token(token)
        keyboard = my_account_keyboard(token, account.type)
        if account.type == AccountType.ADMIN:
            text = strings.MY_ACCOUNT__ADMIN.format(
                last_name=eschtml(field(account.last_name)),
                first_name=eschtml(field(account.first_name)),
                patronymic=eschtml(field(account.patronymic)),
                account_type=get_account_type_str(account.type),
                email=field(account.email),
                item_id=item_id(account.id),
            )
        elif account.type == AccountType.EMPLOYEE:
            try:
                trainings = await service.get_all_trainings(token)
                trainings_field = field(" | ".join([code(i.name) for i in trainings]))
            except AccessError:
                trainings_field = italic(strings.TRAININGS__UNAVAILABLE)
            text = strings.MY_ACCOUNT__EMPLOYEE.format(
                last_name=eschtml(field(account.last_name)),
                first_name=eschtml(field(account.first_name)),
                patronymic=eschtml(field(account.patronymic)),
                account_type=get_account_type_str(account.type),
                email=field(account.email),
                roles=field(" | ".join([code(eschtml(i.name)) for i in account.roles])),
                trainings=trainings_field,
                item_id=item_id(account.id),
            )
        else:
            raise ValueError
        await show(msg, text, is_answer, edited_msg_id, keyboard=keyboard)
    except AccessError:
        raise UnknownError()
    except NotFoundError:
        raise TokenNotValidError()


async def show_log_in_data(token: str, msg: Message, regenerate_access_key: bool = False):
    try:
        log_in_data = await service.get_log_in_data_by_token(token, regenerate_access_key)
        account = await service.get_account_by_token(token)
        keyboard = get_log_in_data_keyboard(log_in_data.access_key)
        text = strings.LOG_IN__DATA.format(first_name=eschtml(account.first_name), access_key=log_in_data.access_key)
        bot_msg = await msg.answer(text, reply_markup=keyboard)
        await asyncio.sleep(60)
        await delete_msg(bot_msg.bot, bot_msg.chat.id, bot_msg.message_id)
    except AccessError:
        raise UnknownError()
    except NotFoundError:
        raise TokenNotValidError()
