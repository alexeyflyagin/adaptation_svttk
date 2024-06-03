from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from data.asvttk_service.models import AccountType
from src.states import MainStates
from src.utils import get_token
from data.asvttk_service import asvttk_service as service


async def to_main_state(msg: Message, state: FSMContext):
    token = await get_token(state)
    account = await service.get_account_by_id(token)
    if account.type == AccountType.ADMIN:
        await state.set_state(MainStates.ADMIN)
    elif account.type == AccountType.EMPLOYEE:
        await state.set_state(MainStates.EMPLOYEE)
    elif account.type == AccountType.STUDENT:
        await state.set_state(MainStates.STUDENT)
