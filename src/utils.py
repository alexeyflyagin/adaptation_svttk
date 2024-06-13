from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from data.asvttk_service.types import AccountData, TrainingData
from src import strings


def get_access_key_link(access_key: str):
    return f"https://t.me/superusername_bot?start={access_key}"


def get_full_name(first_name: str, last_name: Optional[str], patronymic: Optional[str]):
    s = f"{first_name}"
    if last_name:
        s += f" {last_name}"
    if patronymic:
        s += f" {patronymic[0]}"
    return s


def get_full_name_by_account(account: AccountData, full_patronymic: bool = False):
    s = f"{account.first_name}"
    if account.last_name:
        s = f"{account.last_name} {s}"
    if account.patronymic:
        if full_patronymic:
            s += f" {account.patronymic}"
        else:
            s += f" {account.patronymic[0]}"
    return s


def cut_text(it: str, max_symbols: int = 24):
    if len(it) > max_symbols:
        return it[0:max_symbols] + " ..."
    return it


def get_training_status(training: TrainingData):
    status = strings.TRAINING_STATUS__INACTIVE
    if training.date_start:
        status = strings.TRAINING_STATUS__ACTIVE
    if training.date_end:
        status = strings.TRAINING_STATUS__COMPLETED
    return status


async def show(msg: Message, text: str, is_answer: bool, edited_msg_id=None, keyboard=None):
    try:
        if not is_answer and edited_msg_id:
            await msg.bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=edited_msg_id,
                                            reply_markup=keyboard)
        elif not is_answer and not edited_msg_id:
            await msg.edit_text(text=text, reply_markup=keyboard)
        else:
            await msg.answer(text=text, reply_markup=keyboard)
    except TelegramBadRequest as _:
        pass
