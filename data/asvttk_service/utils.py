import random
import time
from typing import Optional

from data.asvttk_service.exceptions import EmptyFieldError


def get_current_time() -> int:
    return int(time.time())


def email_check(email: Optional[str]):
    if email and "@" not in email:
        raise ValueError()


def role_name_check(name: Optional[str]):
    if len(name) > 15:
        raise ValueError()


def training_name_check(it: Optional[str]):
    if it and it.replace(" ", "") == "":
        raise EmptyFieldError("first_name is empty")


def initials_check(first_name: str, last_name: Optional[str], patronymic: Optional[str]):
    if first_name and first_name.replace(" ", "") == "" or not first_name:
        raise ValueError("first_name is empty")
    if last_name and last_name.replace(" ", "") == "":
        raise ValueError("last_name is empty")
    if patronymic and patronymic.replace(" ", "") == "":
        raise ValueError("patronymic is empty")

