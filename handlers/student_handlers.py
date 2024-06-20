import asyncio
from typing import Optional

from aiogram import Router, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, PollAnswer
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.asvttk_service import asvttk_service as service
from data.asvttk_service.exceptions import TokenNotValidError, LevelAnswerAlreadyExistsError, \
    TrainingIsNotActiveError
from data.asvttk_service.models import LevelType
from data.asvttk_service.types import StudentProgressState, StudentProgressData
from handlers.handlers_utils import send_msg, token_not_valid_error_for_callback, get_token, delete_msg, \
    token_not_valid_error, reset_state
from src import strings, commands
from src.states import MainStates

router = Router()

bot: Bot


LAST_ACTIVE_POLL = "last_active_poll"
LAST_MSG_WITH_ACTIONS = "last_msg_with_actions"
START_LEARN_MSG_ID = "start_learn_msg_id"
CLD = "cld"
CONFETTI_MSG_EFFECT_ID = "5046509860389126442"


class LearningCD(CallbackData, prefix="training_progress"):
    token: str
    action: int
    level_id: Optional[int] = None
    level_type: Optional[str] = None

    class Action:
        SHOW = 0
        ANSWER = 1
        SHOW_RESULTS = 2


def start_keyboard(token: str, level_id: int, progress_state: StudentProgressState,
                   level_type: str) -> InlineKeyboardMarkup | None:
    kbb = InlineKeyboardBuilder()
    btn_continue_data = LearningCD(token=token, level_id=level_id, level_type=level_type, action=LearningCD.Action.SHOW)
    if progress_state == StudentProgressState.START:
        kbb.add(InlineKeyboardButton(text=strings.BTN_BEGIN, callback_data=btn_continue_data.pack()))
    elif progress_state == StudentProgressState.LEVEL:
        kbb.add(InlineKeyboardButton(text=strings.BTN_CONTINUE, callback_data=btn_continue_data.pack()))
    elif progress_state == StudentProgressState.COMPLETED:
        btn_show_results_data = LearningCD(token=token, action=LearningCD.Action.SHOW_RESULTS)
        kbb.add(InlineKeyboardButton(text=strings.BTN_SHOW_RESULTS, callback_data=btn_show_results_data.pack()))
    else:
        return
    return kbb.as_markup()


def next_keyboard(token: str, level_id: int, level_type: str) -> InlineKeyboardMarkup | None:
    kbb = InlineKeyboardBuilder()
    btn_answer_data = LearningCD(token=token, level_id=level_id, level_type=level_type, action=LearningCD.Action.ANSWER)
    if level_type == LevelType.INFO:
        kbb.add(InlineKeyboardButton(text=strings.BTN_ALREADY_READ, callback_data=btn_answer_data.pack()))
    elif level_type == LevelType.QUIZ:
        kbb.add(InlineKeyboardButton(text=strings.BTN_NEXT, callback_data=btn_answer_data.pack()))
    else:
        return
    return kbb.as_markup()


@router.callback_query(LearningCD.filter())
async def learning_callback(callback: CallbackQuery, state: FSMContext):
    data = LearningCD.unpack(callback.data)
    try:
        await service.token_validate(data.token)
        if data.action == data.Action.ANSWER:
            await callback.message.edit_reply_markup(reply_markup=None)
            if data.level_type == LevelType.INFO:
                await service.create_level_answer(data.token, data.level_id)
            await show_current_level(data.token, callback.message, state)
            await callback.message.delete()
        if data.action == data.Action.SHOW:
            await restart_handler(callback.message, state)
            await callback.answer()
    except TelegramBadRequest:
        pass
    except TrainingIsNotActiveError:
        await callback.message.answer(strings.TRAINING_PROGRESS__TRAINING_IS_STOPPED)
    except LevelAnswerAlreadyExistsError:
        await restart_handler(callback.message, state)
    except TokenNotValidError:
        await token_not_valid_error_for_callback(callback, state)


@router.poll_answer(MainStates.STUDENT)
async def poll_answer_handler(answer: PollAnswer, state: FSMContext):
    token = await get_token(state)
    state_data = await state.get_data()
    cld = state_data.get(CLD)
    msg = Message.model_validate_json(cld[0])
    msg._bot = bot
    level_id = cld[1]
    try:
        await service.token_validate(token)
        await service.create_level_answer(token, level_id, answer.option_ids)
        await asyncio.sleep(2)
        await show_current_level(token, msg, state)
    except LevelAnswerAlreadyExistsError:
        await restart_handler(msg, state)
    except TrainingIsNotActiveError:
        await msg.answer(strings.TRAINING_PROGRESS__TRAINING_IS_STOPPED)
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


@router.message(MainStates.STUDENT, Command(commands.HELP))
async def restart_handler(msg: Message, state: FSMContext):
    token = await get_token(state)
    state_data = await state.get_data()
    start_learn_msg_id: Optional[int] = state_data.get(START_LEARN_MSG_ID, None)
    await msg.delete()
    try:
        await service.token_validate(token)
        if start_learn_msg_id:
            wait_msg = await msg.answer(strings.WAIT_UPDATING)
            await state.set_state(MainStates.WAIT)
            all_msg_ids = list(range(start_learn_msg_id + 1, msg.message_id))[::-1]
            for i in range(0, len(all_msg_ids), 5):
                tasks = [delete_msg(msg.bot, msg.chat.id, i) for i in all_msg_ids[i: i + 6]]
                await asyncio.gather(*tasks)
            progress = await service.get_student_progress(token)
            level_answered_ids = [i.level_id for i in progress.answers]
            levels = [i for i in progress.training.levels if i.id in level_answered_ids and i.type == LevelType.INFO]
            try:
                for level in levels:
                    await send_msg(msg, level.messages, disable_notification=True)
                await reset_state(state)
                await show_current_level(token, msg, state)
                await wait_msg.delete()
            except TelegramBadRequest:
                await reset_state(state)
                await msg.answer(strings.TELEGRAM_IS_NOT_STABLE)
                await wait_msg.delete()
    except TokenNotValidError:
        await token_not_valid_error(msg, state)


async def show_start(token: str, msg: Message, state: FSMContext):
    progress = await service.get_student_progress(token)
    bot_msg = await send_msg(msg, progress.training.message)
    await state.update_data({START_LEARN_MSG_ID: bot_msg.message_id})
    if progress.progress_state != StudentProgressState.START:
        await restart_handler(msg, state)
        return
    keyboard = start_keyboard(token, progress.current_level.id, progress.progress_state, progress.current_level.type)
    await msg.answer(text=strings.TRAINING_PROGRESS__BEGIN, reply_markup=keyboard)


async def show_current_level(token: str, msg: Message, state: FSMContext):
    progress = await service.get_student_progress(token)
    try:
        if progress.progress_state == StudentProgressState.COMPLETED:
            text = strings.TRAINING_PROGRESS__COMPLETED.format(training_name=progress.training.name)
            await msg.answer(text, message_effect_id=CONFETTI_MSG_EFFECT_ID)
            return
        level_msg = await send_msg(msg, progress.current_level.messages)
        await service.training_is_not_started_check(token, progress.training.id)
        if progress.current_level.type == LevelType.QUIZ:
            await state.update_data({CLD: [level_msg.model_dump_json(), progress.current_level.id]})
        if progress.current_level.type == LevelType.INFO:
            await show_next_keyboard(token, msg, progress)
    except TrainingIsNotActiveError:
        await msg.answer(strings.TRAINING_PROGRESS__TRAINING_IS_STOPPED)
    except TelegramBadRequest:
        await msg.answer(strings.TELEGRAM_IS_NOT_STABLE)


async def show_next_keyboard(token: str, msg: Message, progress: Optional[StudentProgressData] = None):
    if not progress:
        progress = await service.get_student_progress(token)
    keyboard = next_keyboard(token, progress.current_level.id, progress.current_level.type)
    text = strings.TRAINING_PROGRESS__NEXT__INFO
    if progress.current_level.type == LevelType.QUIZ:
        text = strings.TRAINING_PROGRESS__NEXT__QUIZ
    await msg.answer(text=text, reply_markup=keyboard, disable_notification=True)
