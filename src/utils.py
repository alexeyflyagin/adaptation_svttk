from functools import reduce
from typing import Optional, Any

from aiogram.enums import ContentType, PollType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAnimation,
                           InputMediaAudio)
from aiogram_album import AlbumMessage

from data.asvttk_service.exceptions import InitialsValueError
from data.asvttk_service.models import LevelType, FileType, AccountType
from data.asvttk_service.types import AccountData, TrainingData
from src import strings


CONTENT_TYPE__MEDIA_GROUP = "media_group"
START_SESSION_MSG_ID = "start_session_msg_id"
END_PREVIOUS_SESSION_MSG_ID = "end_previous_session_msg_id"
UPDATED_MSG_ID = "updated_msg_id"
UPDATED_MSG = "updated_msg"
UPDATED_ITEM_ID = "updated_item_id"


def get_level_type_from_content_type(content_type: str, arg: Optional[Any] = None) -> str:
    if content_type in [CONTENT_TYPE__MEDIA_GROUP, ContentType.TEXT, ContentType.AUDIO, ContentType.VIDEO,
                        ContentType.PHOTO, ContentType.DOCUMENT, ContentType.LOCATION, ContentType.ANIMATION,
                        ContentType.CONTACT, ContentType.STICKER]:
        return LevelType.INFO
    elif content_type == ContentType.POLL and arg == PollType.QUIZ:
        return LevelType.QUIZ
    else:
        raise TypeError()


def get_files_from_msg(msg: AlbumMessage | Message) -> dict[str, str]:
    if msg.content_type == ContentType.TEXT:
        return {}
    elif msg.content_type == ContentType.PHOTO:
        return {msg.photo[-2].file_id: FileType.PHOTO}
    elif msg.content_type == ContentType.VIDEO:
        return {msg.video.file_id: FileType.VIDEO}
    elif msg.content_type == ContentType.DOCUMENT:
        return {msg.document.file_id: FileType.DOCUMENT}
    elif msg.content_type == CONTENT_TYPE__MEDIA_GROUP:
        d = [get_files_from_msg(i) for i in msg.messages]
        return reduce(lambda x, y: {**x, **y}, d)
    else:
        raise TypeError()


def get_input_media_by_level_type(msg: Message, show_caption_above_media: bool | None = None) -> \
        (InputMediaPhoto | InputMediaVideo | InputMediaDocument | InputMediaAnimation | InputMediaAudio):
    if msg.content_type == ContentType.PHOTO:
        return InputMediaPhoto(media=msg.photo[-1].file_id, caption=msg.html_text, caption_entities=msg.caption_entities,
                               show_caption_above_media=show_caption_above_media, has_spoiler=msg.has_media_spoiler)
    elif msg.content_type == ContentType.VIDEO:
        return InputMediaVideo(media=msg.video.file_id, caption=msg.html_text,
                               caption_entities=msg.caption_entities, width=msg.video.width,
                               height=msg.video.height, duration=msg.video.duration, has_spoiler=msg.has_media_spoiler,
                               show_caption_above_media=show_caption_above_media)
    elif msg.content_type == ContentType.DOCUMENT:
        return InputMediaDocument(media=msg.document.file_id, caption=msg.html_text,
                                  caption_entities=msg.caption_entities)
    elif msg.content_type == ContentType.ANIMATION:
        return InputMediaAnimation(media=msg.animation.file_id, has_spoiler=msg.has_media_spoiler,
                                   caption_entities=msg.caption_entities,
                                   height=msg.animation.height, duration=msg.animation.duration, caption=msg.html_text,
                                   show_caption_above_media=show_caption_above_media, width=msg.animation.width)
    elif msg.content_type == ContentType.AUDIO:
        return InputMediaAudio(media=msg.audio.file_id, caption=msg.html_text,
                               caption_entities=msg.caption_entities, duration=msg.audio.duration,
                               performer=msg.audio.performer, title=msg.audio.title)
    else:
        raise TypeError()


def get_account_type_str(account_type: AccountType) -> str:
    if account_type == AccountType.ADMIN:
        return strings.ACCOUNT_TYPE__ADMIN
    elif account_type == AccountType.EMPLOYEE:
        return strings.ACCOUNT_TYPE__EMPLOYEE
    elif account_type == AccountType.STUDENT:
        return strings.ACCOUNT_TYPE__STUDENT
    else:
        raise TypeError


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


def is_started_training(training: TrainingData):
    if training.date_start and not training.date_end:
        return True
    return False


def get_initials_from_text(text: str, has_none: bool = False) -> list[str]:
    initials = [i.replace(" ", "") for i in text.split()]
    if len(initials) != 3 or initials[1] == '-':
        raise InitialsValueError()
    if has_none:
        initials = [i if i != "-" else None for i in initials]
    return initials


def get_training_status(training: TrainingData):
    status = strings.TRAINING_STATUS__INACTIVE
    if is_started_training(training):
        status = strings.TRAINING_STATUS__ACTIVE
    return status


async def show(msg: Message, text: str, is_answer: bool, edited_msg_id=None, keyboard=None, is_delete: bool = True):
    try:
        if not is_answer and edited_msg_id:
            await msg.bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=edited_msg_id,
                                            reply_markup=keyboard)
        elif not is_answer and not edited_msg_id:
            await msg.edit_text(text=text, reply_markup=keyboard)
        else:
            await msg.answer(text=text, reply_markup=keyboard)
            if is_delete and edited_msg_id:
                await msg.bot.edit_message_reply_markup(msg.chat.id, edited_msg_id, reply_markup=None)
    except TelegramBadRequest as _:
        pass
