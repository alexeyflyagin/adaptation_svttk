from typing import Optional

from aiogram.fsm.context import FSMContext

from custom_storage import TOKEN


def key_link(key: str):
    return f"https://t.me/superusername_bot?start={key}"


async def get_token(state: FSMContext):
    state_data = await state.get_data()
    return state_data.get(TOKEN, None)


def get_full_name(first_name: str, last_name: Optional[str], patronymic: Optional[str]):
    s = f"{first_name}"
    if last_name:
        s += f" {last_name}"
    if patronymic:
        s += f" {patronymic[0]}"
    return s
