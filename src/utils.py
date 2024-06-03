from aiogram.fsm.context import FSMContext

from custom_storage import TOKEN


def key_link(key: str):
    return f"https://t.me/superusername_bot?start={key}"


async def get_token_from_state(state: FSMContext):
    state_data = await state.get_data()
    return state_data.get(TOKEN, None)
