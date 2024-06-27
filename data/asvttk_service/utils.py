import time
from typing import Optional

from aiogram.enums import ContentType, PollType
from aiogram.types import Message

from data.asvttk_service import strings
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


def get_content_text(msgs: [Message]):
    if len(msgs) == 0:
        raise ValueError()
    msg = msgs[0]
    content_text = msg.text if msg.text else msg.caption
    content_text = content_text if content_text else None
    if msg.content_type == ContentType.POLL:
        content_text = msg.poll.question
    return content_text


def get_content_type_str(msgs: list[Message]):
    if len(msgs) == 0:
        raise ValueError()
    msg = msgs[0]
    if len(msgs) == 1:
        if msg.content_type == ContentType.TEXT:
            return strings.CONTENT_TYPE__TEXT
        elif msg.content_type == ContentType.PHOTO:
            return strings.CONTENT_TYPE__PHOTO
        elif msg.content_type == ContentType.VIDEO:
            return strings.CONTENT_TYPE__VIDEO
        elif msg.content_type == ContentType.DOCUMENT:
            return strings.CONTENT_TYPE__DOCUMENT
        elif msg.content_type == ContentType.AUDIO:
            return strings.CONTENT_TYPE__AUDIO
        elif msg.content_type == ContentType.STICKER:
            return strings.CONTENT_TYPE__STICKER
        elif msg.content_type == ContentType.ANIMATION:
            return strings.CONTENT_TYPE__ANIMATION
        elif msg.content_type == ContentType.CONTACT:
            return strings.CONTENT_TYPE__CONTACT
        elif msg.content_type == ContentType.LOCATION:
            return strings.CONTENT_TYPE__LOCATION
        elif msg.content_type == ContentType.POLL and msg.poll.type == PollType.QUIZ:
            return strings.CONTENT_TYPE__POLL__QUIZ
        elif msg.content_type == ContentType.POLL:
            return strings.CONTENT_TYPE__POLL
        else:
            return TypeError()
    else:
        return strings.CONTENT_TYPE__MEDIA_GROUP


def get_file_count(msgs: list[Message]):
    if len(msgs) == 0:
        raise ValueError()
    msg = msgs[0]
    if len(msgs) == 1:
        if msg.content_type in [ContentType.TEXT, ContentType.POLL, ContentType.LOCATION, ContentType.CONTACT,
                                ContentType.STICKER]:
            return 0
        elif msg.content_type in [ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT, ContentType.AUDIO,
                                  ContentType.ANIMATION]:
            return 1
        else:
            return TypeError()
    else:
        return len(msgs)
