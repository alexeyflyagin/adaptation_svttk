from aiogram import Router
from aiogram.filters import CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers import admin_roles_handlers, handlers_utils, last_handlers, admin_employees_handlers
from src import strings, commands
from custom_storage import TOKEN
from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import KeyNotFoundError
from src.states import RoleCreateStates, RoleRenameStates, EmployeeCreateStates, EmployeeEditEmailStates
from src.utils import key_link, get_full_name_by_account

router = Router()
router.include_routers(admin_roles_handlers.router)
router.include_routers(admin_employees_handlers.router)
router.include_routers(last_handlers.router)


@router.message(Command(commands.START))
async def start_handler(msg: Message, state: FSMContext, command: CommandObject):
    if not command.args:
        await msg.answer(strings.LOG_IN__NO_ACCESS_KEY)
        return
    user_id = msg.from_user.id
    try:
        log_in_data = await service.log_in(user_id, key=command.args)
        account = await service.get_account_by_id(log_in_data.token)
        await state.update_data({TOKEN: log_in_data.token})
        await handlers_utils.reset_state(state)
        if log_in_data.is_first:
            await msg.answer(strings.LOG_IN__SUCCESS__FIRST.format(first_name=account.first_name,
                                                                   access_key=log_in_data.access_key))
        else:
            await msg.answer(strings.LOG_IN__SUCCESS.format(first_name=account.first_name))
    except KeyNotFoundError:
        await msg.answer(strings.LOG_IN__ACCOUNT_NOT_FOUND)


@router.message(RoleCreateStates(), Command(commands.CANCEL))
@router.message(RoleRenameStates(), Command(commands.CANCEL))
@router.message(EmployeeEditEmailStates(), Command(commands.CANCEL))
@router.message(EmployeeCreateStates(), Command(commands.CANCEL))
async def cancel_handler(msg: Message, state: FSMContext):
    await handlers_utils.reset_state(state)
    await msg.answer(strings.ACTION_CANCELED)
