import time
import uuid
from typing import Optional

from data.asvttk_service.exceptions import EmailValueError, InitialsValueError, EmptyFieldError


def generate_access_key() -> str:
    return str(uuid.uuid4()).replace("-", "")[16:]


def generate_session_token() -> str:
    return str(uuid.uuid4()).replace("-", "")[16:]


def get_current_time() -> int:
    return int(time.time())


def email_check(email: Optional[str]):
    if email and "@" not in email:
        raise EmailValueError()


def empty_check(it: Optional[str]):
    if it and it.replace(" ", "") == "":
        raise EmptyFieldError("first_name is empty")


def initials_check(first_name: str, last_name: Optional[str], patronymic: Optional[str]):
    if first_name and first_name.replace(" ", "") == "":
        raise InitialsValueError("first_name is empty")
    if last_name and last_name.replace(" ", "") == "":
        raise InitialsValueError("last_name is empty")
    if patronymic and last_name.replace(" ", "") == "":
        raise InitialsValueError("patronymic is empty")

