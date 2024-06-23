from html import escape
from typing import Optional, Any

import validators
from aiogram.enums import ContentType, PollType
from aiogram.types import Message
from aiogram_album import AlbumMessage
from typeguard import typechecked

from src.strings import code
from src.utils import CONTENT_TYPE__POLL__QUIZ, get_content_type_str


class ValueNotValidError(Exception):
    def __init__(self, error_msg: str):
        self.error_msg = error_msg


math_symbols = "+-*/=<>"
special_chars = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
digits = "0123456789"
latin_low = "abcdefghijklmnopqrstuvwxyz"
latin_up = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
russian_low = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
russian_up = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


ERROR__EMPTY_VALUE = "Значение не может быть пустым."
ERROR__EMPTY_VALUE__ARG = "Значение {arg} не может быть пустым."
ERROR__CONTENT_TYPE = """Контент некорректен. Доступные типы контента: 
{allows_content_types}."""
ERROR__MAX_LIMIT = """Значение не должно превышать {limit_value}."""
ERROR__INVALID_CHARS = """Недопустимые символы:  {chars}"""
ERROR__EMAIL = """Некорректный email."""
ERROR__REQUIRED_FILL = """Обязательные значения: {required}."""
ERROR__FULL_NAME_INTEGRITY__MORE = """Вы ввели больше аргументов, чем {than}."""
ERROR__FULL_NAME_INTEGRITY__LESS = """Вы ввели меньше аргументов, чем {than}."""


def __is_not_empty(v: Any, arg: str = ""):
    if not v:
        if arg:
            raise ValueNotValidError(ERROR__EMPTY_VALUE__ARG.format(arg=arg))
        else:
            raise ValueNotValidError(ERROR__EMPTY_VALUE)


def __get_invalid_chars(v: Any, allows_chars: str) -> str:
    return "".join(set([i for i in v if i not in allows_chars]))


def __show_invalid_chars(chars: str):
    return "  ".join([code(escape(i)) for i in chars])


@property
def latin_symbols():
    return latin_low + latin_up


@property
def russian_symbols():
    return russian_low + russian_up


@typechecked
def valid_content_type_msg(v: Message | AlbumMessage, *args):
    content_type = v.content_type
    if content_type == ContentType.POLL and v.poll.type == PollType.QUIZ:
        content_type = CONTENT_TYPE__POLL__QUIZ
    allow_types = list(args)
    if not allow_types:
        raise ValueError("The field allow_types is empty!")
    if content_type not in list(args):
        allow_types_str = [code(get_content_type_str(i)) for i in allow_types]
        raise ValueNotValidError(ERROR__CONTENT_TYPE.format(allows_content_types=", ".join(allow_types_str)))


@typechecked
def valid_role_name(v: Optional[str]):
    __is_not_empty(v)
    if len(v) > 15:
        raise ValueNotValidError(ERROR__MAX_LIMIT.format(limit_value="15 символов"))


@typechecked
def valid_full_name(full_name: str, empty_v: str = "-",
                    null_if_empty: bool = False) -> (Optional[str], str, Optional[str]):
    __is_not_empty(full_name)
    fn_list = [i.replace(" ", "") for i in full_name.split()]
    if len(fn_list) > 3:
        raise ValueNotValidError(ERROR__FULL_NAME_INTEGRITY__MORE.format(than="3"))
    if len(fn_list) < 3:
        raise ValueNotValidError(ERROR__FULL_NAME_INTEGRITY__LESS.format(than="3"))
    if fn_list[1] == empty_v or fn_list[1] is None:
        raise ValueNotValidError(ERROR__REQUIRED_FILL.format(required=f" {code('Имя')}"))
    allow_chars = russian_up + russian_low + latin_low + latin_up + "._()-'"
    s = "".join([__get_invalid_chars(fn_list[i], allow_chars) for i in range(3)])
    s = "".join(list(set(s)))
    if s:
        raise ValueNotValidError(ERROR__INVALID_CHARS.format(chars=__show_invalid_chars(s)))
    if null_if_empty:
        fn_list = [None if i == empty_v else i for i in fn_list]
    return fn_list[0], fn_list[1], fn_list[2]


@typechecked
def valid_email(v: str, empty_v: str = "-", null_if_empty: bool = False) -> Optional[str]:
    __is_not_empty(v)
    res = v
    if res == empty_v and null_if_empty:
        res = None
    if not validators.email(v):
        raise ValueNotValidError(ERROR__EMAIL)
    return res


@typechecked
def valid_name(v: str) -> Optional[str]:
    __is_not_empty(v)
    res = v
    allow_chars = russian_up + russian_low + latin_low + latin_up + special_chars + " "
    s = __get_invalid_chars(v, allow_chars)
    if s:
        raise ValueNotValidError(ERROR__INVALID_CHARS.format(chars=__show_invalid_chars(s)))
    return res



