import asyncio
from src.strings import eschtml
from typing import Optional, Any

from aiogram import Bot
from aiogram.enums import ContentType, PollType
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from custom_storage import TOKEN
from data.asvttk_service.models import AccountType
from src import strings
from src.states import MainStates
from data.asvttk_service import asvttk_service as service
from src.utils import get_input_media_by_level_type, START_SESSION_MSG_ID, UPDATED_MSG, UPDATED_ITEM

ADDITIONAL_SESSION_MSG_IDS = "additional_session_msgs"


async def reset_state(state: FSMContext):
    token = await get_token(state)
    if token:
        account = await service.get_account_by_id(token)
        if account.type == AccountType.ADMIN:
            await state.set_state(MainStates.ADMIN)
        elif account.type == AccountType.EMPLOYEE:
            await state.set_state(MainStates.EMPLOYEE)
        elif account.type == AccountType.STUDENT:
            await state.set_state(MainStates.STUDENT)
    else:
        await state.set_state(None)


async def get_token(state: FSMContext):
    state_data = await state.get_data()
    state_token = state_data.get(TOKEN, None)
    return state_token


async def set_updated_msg(state: FSMContext, message_id: int, args: Optional[list[Any]] = None):
    await state.update_data({UPDATED_MSG: (message_id, args)})


async def get_updated_msg(state: FSMContext):
    state_data = await state.get_data()
    update_msg = state_data.get(UPDATED_MSG, None)
    if update_msg is None:
        raise ValueError()
    if UPDATED_MSG in state_data:
        state_data.pop(UPDATED_MSG)
    return update_msg


async def set_updated_item(state: FSMContext, item_id: int, args: Optional[list[Any]] = None):
    await state.update_data({UPDATED_ITEM: (item_id, args)})


async def get_updated_item(state: FSMContext):
    state_data = await state.get_data()
    update_msg = state_data.get(UPDATED_ITEM, None)
    if update_msg is None:
        raise ValueError()
    return update_msg


async def delete_updated_item(state: FSMContext):
    state_data = await state.get_data()
    if UPDATED_ITEM in state_data:
        state_data.pop(UPDATED_ITEM)


async def token_not_valid_error(msg: Message, state: FSMContext):
    await log_out(msg, state, log_out_text=strings.SESSION_ERROR)


async def token_not_valid_error_for_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await log_out(callback.message, state, log_out_text=strings.SESSION_ERROR)


async def unknown_error(msg: Message, state: FSMContext, canceled: bool = True) -> Message:
    res = await msg.answer(strings.ERROR__UNKNOWN)
    if canceled:
        await msg.answer(strings.ACTION_CANCELED)
    await reset_state(state)
    return res


async def unknown_error_for_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer(strings.ERROR__UNKNOWN)


async def access_error(msg: Message, state: FSMContext, canceled: bool = True):
    res = await msg.answer(strings.ERROR__ACCESS)
    if canceled:
        await msg.answer(strings.ACTION_CANCELED)
    await reset_state(state)
    return res


async def access_error_for_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer(strings.ERROR__ACCESS)


async def delete_msg(bot: Bot, chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except TelegramBadRequest as _:
        pass


async def send_msg(c_msg: Message, msgs: list[Message], disable_notification: bool = False) -> Message:
    if len(msgs) == 0:
        raise ValueError()
    if len(msgs) == 1:
        msg = msgs[0]
        if msg.content_type == ContentType.TEXT:
            res = await c_msg.answer(text=msg.html_text, message_effect_id=msg.effect_id,
                                     disable_notification=disable_notification)
        elif msg.content_type == ContentType.PHOTO:
            res = await c_msg.answer_photo(photo=msg.photo[-1].file_id, caption=msg.html_text,
                                           caption_entities=msg.caption_entities, message_effect_id=msg.effect_id,
                                           show_caption_above_media=msg.show_caption_above_media,
                                           has_spoiler=msg.has_media_spoiler, disable_notification=disable_notification)
        elif msg.content_type == ContentType.VIDEO:
            res = await c_msg.answer_video(video=msg.video.file_id, caption=msg.html_text, duration=msg.video.duration,
                                           width=msg.video.width, height=msg.video.height,
                                           caption_entities=msg.caption_entities, has_spoiler=msg.has_media_spoiler,
                                           show_caption_above_media=msg.show_caption_above_media,
                                           message_effect_id=msg.effect_id, disable_notification=disable_notification)
        elif msg.content_type == ContentType.DOCUMENT:
            res = await c_msg.answer_document(document=msg.document.file_id, caption_entities=msg.caption_entities,
                                              caption=msg.html_text,
                                              message_effect_id=msg.effect_id,
                                              disable_notification=disable_notification)
        elif msg.content_type == ContentType.POLL:
            res = await c_msg.answer_poll(question=msg.poll.question, options=[i.text for i in msg.poll.options],
                                          explanation_entities=msg.poll.explanation_entities, is_anonymous=False,
                                          allows_multiple_answers=msg.poll.allows_multiple_answers, type=msg.poll.type,
                                          correct_option_id=msg.poll.correct_option_id, message_effect_id=msg.effect_id,
                                          explanation=eschtml(msg.poll.explanation) if msg.poll.explanation else None,
                                          disable_notification=disable_notification,
                                          question_entities=msg.poll.question_entities)
        elif msg.content_type == ContentType.AUDIO:
            res = await c_msg.answer_audio(audio=msg.audio.file_id, caption=msg.html_text,
                                           performer=msg.audio.performer, caption_entities=msg.caption_entities,
                                           message_effect_id=msg.effect_id, duration=msg.audio.duration,
                                           title=msg.audio.title, disable_notification=disable_notification)
        elif msg.content_type == ContentType.STICKER:
            res = await c_msg.answer_sticker(sticker=msg.sticker.file_id, emoji=msg.sticker.emoji,
                                             message_effect_id=msg.effect_id, disable_notification=disable_notification)
        elif msg.content_type == ContentType.ANIMATION:
            res = await c_msg.answer_animation(animation=msg.animation.file_id, duration=msg.animation.duration,
                                               width=msg.animation.width, height=msg.animation.height,
                                               caption=msg.html_text, caption_entities=msg.caption_entities,
                                               message_effect_id=msg.effect_id, has_spoiler=msg.has_media_spoiler,
                                               show_caption_above_media=msg.show_caption_above_media,
                                               disable_notification=disable_notification)
        elif msg.content_type == ContentType.CONTACT:
            res = await c_msg.answer_contact(phone_number=msg.contact.phone_number, first_name=msg.contact.first_name,
                                             last_name=msg.contact.last_name, vcard=msg.contact.vcard,
                                             message_effect_id=msg.effect_id, disable_notification=disable_notification)
        elif msg.content_type == ContentType.LOCATION:
            res = await c_msg.answer_location(latitude=msg.location.latitude, longitude=msg.location.longitude,
                                              horizontal_accuracy=msg.location.horizontal_accuracy,
                                              heading=msg.location.heading, message_effect_id=msg.effect_id,
                                              proximity_alert_radius=msg.location.proximity_alert_radius,
                                              disable_notification=disable_notification)
        else:
            raise ValueError()
    else:
        msg = msgs[-1]
        media = [get_input_media_by_level_type(i, msgs[0].show_caption_above_media) for i in msgs]
        res = await c_msg.answer_media_group(media=media, message_effect_id=msg.effect_id,
                                             disable_notification=disable_notification)
    return res


async def add_additional_msg_id(state: FSMContext, it: int):
    state_data = await state.get_data()
    session_msgs = state_data.get(ADDITIONAL_SESSION_MSG_IDS, [])
    await state.update_data({ADDITIONAL_SESSION_MSG_IDS: session_msgs + [it]})


async def log_out(msg: Message, state: FSMContext, new_token: Optional[str] = None,
                  log_out_text: Optional[str] = None):
    if log_out_text:
        log_out_msg = await msg.answer(log_out_text)
        await asyncio.sleep(1)
    else:
        log_out_msg = await msg.answer("-")
        await log_out_msg.delete()
    state_data = await state.get_data()
    start_session_msg_id = state_data.get(START_SESSION_MSG_ID, None)
    token = await get_token(state)
    await service.log_out(token)
    await state.set_data({TOKEN: new_token, START_SESSION_MSG_ID: msg.message_id})
    if start_session_msg_id:
        wait_msg = await msg.answer(strings.WAIT_CLEAR_PREVIOUS_SESSION)
        await state.set_state(MainStates.CLEAR_PREVIOUS_SESSION)
        end_session_msg_id = log_out_msg.message_id
        all_msg_ids = list(range(start_session_msg_id, end_session_msg_id))[::-1]
        for i in range(0, len(all_msg_ids), 5):
            tasks = [delete_msg(msg.bot, msg.chat.id, i) for i in all_msg_ids[i: i + 6]]
            await asyncio.gather(*tasks)
        await delete_msg(wait_msg.bot, wait_msg.chat.id, wait_msg.message_id)
    await reset_state(state)
    if log_out_msg:
        await delete_msg(msg.bot, msg.chat.id, log_out_msg.message_id)


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


def get_content_text(msgs: [Message]):
    if len(msgs) == 0:
        raise ValueError()
    msg = msgs[0]
    content_text = msg.text if msg.text else msg.caption
    content_text = content_text if content_text else None
    if msg.content_type == ContentType.POLL:
        content_text = msg.poll.question
    return content_text


def get_content_html_text(msgs: [Message]) -> str | None:
    if len(msgs) == 0:
        raise ValueError()
    msg = msgs[0]
    content_text = msg.html_text if msg.html_text else None
    if msg.content_type == ContentType.POLL:
        content_text = msg.poll.question
    return content_text
