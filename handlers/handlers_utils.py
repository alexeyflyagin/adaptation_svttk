from aiogram.enums import ContentType, PollType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from custom_storage import TOKEN
from data.asvttk_service.models import AccountType
from src import strings
from src.states import MainStates
from data.asvttk_service import asvttk_service as service
from src.utils import get_input_media_by_level_type


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


async def token_not_valid_error(msg: Message, state: FSMContext):
    await state.update_data({TOKEN: None})
    await reset_state(state)
    await msg.answer(text=strings.SESSION_ERROR)


async def token_not_valid_error_for_callback(callback: CallbackQuery):
    await callback.answer(strings.SESSION_ERROR)
    await callback.message.edit_reply_markup(inline_message_id=None)


async def send_msg(c_msg: Message, msgs: list[Message]) -> Message:
    if len(msgs) == 0:
        raise ValueError()
    if len(msgs) == 1:
        msg = msgs[0]
        if msg.content_type == ContentType.TEXT:
            res = await c_msg.answer(text=msg.html_text, message_effect_id=msg.effect_id)
        elif msg.content_type == ContentType.PHOTO:
            res = await c_msg.answer_photo(photo=msg.photo[-1].file_id, caption=msg.html_text,
                                           caption_entities=msg.caption_entities, message_effect_id=msg.effect_id,
                                           show_caption_above_media=msg.show_caption_above_media,
                                           has_spoiler=msg.has_media_spoiler)
        elif msg.content_type == ContentType.VIDEO:
            res = await c_msg.answer_video(video=msg.video.file_id, caption=msg.html_text, duration=msg.video.duration,
                                           width=msg.video.width, height=msg.video.height,
                                           caption_entities=msg.caption_entities, has_spoiler=msg.has_media_spoiler,
                                           show_caption_above_media=msg.show_caption_above_media,
                                           message_effect_id=msg.effect_id)
        elif msg.content_type == ContentType.DOCUMENT:
            res = await c_msg.answer_document(document=msg.document.file_id, caption_entities=msg.caption_entities,
                                              caption=msg.caption,
                                              message_effect_id=msg.effect_id)
        elif msg.content_type == ContentType.POLL:
            res = await c_msg.answer_poll(question=msg.poll.question, options=[i.text for i in msg.poll.options],
                                          explanation_entities=msg.poll.explanation_entities, is_anonymous=False,
                                          allows_multiple_answers=msg.poll.allows_multiple_answers, type=msg.poll.type,
                                          correct_option_id=msg.poll.correct_option_id, message_effect_id=msg.effect_id,
                                          explanation=msg.poll.explanation,
                                          question_entities=msg.poll.question_entities)
        elif msg.content_type == ContentType.AUDIO:
            res = await c_msg.answer_audio(audio=msg.audio.file_id, caption=msg.caption, performer=msg.audio.performer,
                                           caption_entities=msg.caption_entities, message_effect_id=msg.effect_id,
                                           duration=msg.audio.duration, title=msg.audio.title)
        elif msg.content_type == ContentType.STICKER:
            res = await c_msg.answer_sticker(sticker=msg.sticker.file_id, emoji=msg.sticker.emoji,
                                             message_effect_id=msg.effect_id)
        elif msg.content_type == ContentType.ANIMATION:
            res = await c_msg.answer_animation(animation=msg.animation.file_id, duration=msg.animation.duration,
                                               width=msg.animation.width, height=msg.animation.height,
                                               caption=msg.caption, caption_entities=msg.caption_entities,
                                               message_effect_id=msg.effect_id, has_spoiler=msg.has_media_spoiler,
                                               show_caption_above_media=msg.show_caption_above_media)
        elif msg.content_type == ContentType.CONTACT:
            res = await c_msg.answer_contact(phone_number=msg.contact.phone_number, first_name=msg.contact.first_name,
                                             last_name=msg.contact.last_name, vcard=msg.contact.vcard,
                                             message_effect_id=msg.effect_id)
        elif msg.content_type == ContentType.LOCATION:
            res = await c_msg.answer_location(latitude=msg.location.latitude, longitude=msg.location.longitude,
                                              horizontal_accuracy=msg.location.horizontal_accuracy,
                                              heading=msg.location.heading, message_effect_id=msg.effect_id,
                                              proximity_alert_radius=msg.location.proximity_alert_radius)
        else:
            raise ValueError()
    else:
        msg = msgs[-1]
        media = [get_input_media_by_level_type(i, msgs[0].show_caption_above_media) for i in msgs]
        res = await c_msg.answer_media_group(media=media, message_effect_id=msg.effect_id)
    return res


def get_content_type_srt(msgs: [Message]):
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

