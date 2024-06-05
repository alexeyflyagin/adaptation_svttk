from typing import Optional

from data.asvttk_service.types import AccountData


def key_link(key: str):
    return f"https://t.me/superusername_bot?start={key}"


def get_full_name(first_name: str, last_name: Optional[str], patronymic: Optional[str]):
    s = f"{first_name}"
    if last_name:
        s += f" {last_name}"
    if patronymic:
        s += f" {patronymic[0]}"
    return s


def get_full_name_by_account(account: AccountData):
    s = f"{account.first_name}"
    if account.last_name:
        s += f" {account.last_name}"
    if account.patronymic:
        s += f" {account.patronymic[0]}"
    return s


def cut_text(it: str, max_symbols: int = 24):
    if len(it) > max_symbols:
        return it[0:max_symbols] + " ..."
    return it
