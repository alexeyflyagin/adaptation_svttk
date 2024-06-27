from datetime import datetime
from typing import Optional

from aiogram.enums import ContentType
from aiogram.types import Message

from data.asvttk_service.models import AccountOrm, RoleOrm, TrainingOrm, LevelOrm, LevelAnswerOrm
from data.asvttk_service.types import AccountData, RoleData, TrainingData, EmployeeData, StudentData, LevelData, \
    LevelAnswerData, StudentProgressState
from data.asvttk_service.utils import get_content_text, get_content_type_str, get_file_count
from data.asvttk_service.xlsx_generation.tables import LevelRT, TrainingRT, StudentRT, RLevelType, RTrainingState, \
    RStudentState, AnswerRT


def account_orm_to_account_data(it: AccountOrm) -> AccountData:
    return AccountData(
        id=it.id,
        type=it.type,
        email=it.email,
        date_create=it.date_create,
        first_name=it.first_name,
        last_name=it.last_name,
        patronymic=it.patronymic,
        training_id=it.training_id,
        date_complete_training=it.date_complete_training
    )


def account_orm_to_employee_data(it: AccountOrm, roles: list[RoleData]) -> EmployeeData:
    return EmployeeData(
        id=it.id,
        type=it.type,
        email=it.email,
        date_create=it.date_create,
        first_name=it.first_name,
        last_name=it.last_name,
        patronymic=it.patronymic,
        training_id=it.training_id,
        date_complete_training=it.date_complete_training,
        roles=roles
    )


def account_orm_to_student_data(it: AccountOrm, training: Optional[TrainingData],
                                answers: Optional[list[LevelAnswerData]]) -> StudentData:
    return StudentData(
        id=it.id,
        type=it.type,
        email=it.email,
        date_create=it.date_create,
        first_name=it.first_name,
        last_name=it.last_name,
        patronymic=it.patronymic,
        training_id=it.training_id,
        date_complete_training=it.date_complete_training,
        training=training,
        answers=answers,
    )


def training_orm_to_training_data(it: TrainingOrm, students: Optional[list[AccountData]],
                                  levels: Optional[list[LevelData]]) -> TrainingData:
    return TrainingData(
        id=it.id,
        name=it.name,
        message=it.message,
        date_create=it.date_create,
        date_start=it.date_start,
        date_end=it.date_end,
        students=students,
        levels=levels,
    )


def level_orm_to_level_data(it: LevelOrm, order: Optional[int], training: Optional[TrainingData],
                            answers: Optional[list[LevelAnswerData]]) -> LevelData:
    return LevelData(
        id=it.id,
        order=order,
        previous_level_id=it.previous_level_id,
        next_level_id=it.next_level_id,
        training_id=it.training_id,
        type=it.type,
        date_create=it.date_create,
        title=it.title,
        messages=it.messages,
        training=training,
        answers=answers,
    )


# noinspection PyTypeChecker
def level_orm_to_level_rt(it: LevelOrm, order: int, level_type: RLevelType) -> LevelRT:
    options = None
    correct_option = None
    explanation = None
    if it.messages[0].content_type == ContentType.POLL:
        options = [i.text for i in it.messages[0].poll.options]
        correct_option = options[it.messages[0].poll.correct_option_id]
        explanation = it.messages[0].poll.explanation
    return LevelRT(
        id=it.id,
        num=order,
        level_type=level_type,
        date_create=datetime.utcfromtimestamp(it.date_create),
        title=it.title,
        text=get_content_text(it.messages),
        content_type=get_content_type_str(it.messages),
        file_count=get_file_count(it.messages),
        options=options,
        correct_option=correct_option,
        explanation=explanation,
    )


# noinspection PyTypeChecker
def training_orm_to_training_rt(it: TrainingOrm, state: RTrainingState) -> TrainingRT:
    date_start = None
    date_complete = None
    if it.date_start:
        date_start = datetime.utcfromtimestamp(it.date_start)
    if it.date_end:
        date_complete = datetime.utcfromtimestamp(it.date_end)
    return TrainingRT(
        id=it.id,
        name=it.name,
        start_msg=get_content_text(it.message),
        date_create=datetime.utcfromtimestamp(it.date_create),
        state=state,
        date_start=date_start,
        date_complete=date_complete,
    )


def account_orm_to_student_rt(it: AccountOrm, state: RStudentState, progress_percent: float) -> StudentRT:
    return StudentRT(
        id=it.id,
        first_name=it.first_name,
        last_name=it.last_name,
        patronymic=it.patronymic,
        date_create=datetime.utcfromtimestamp(it.date_create),
        state=state,
        progress=progress_percent,
    )


# noinspection PyTypeChecker
def level_answer_orm_to_answer_rt(it: LevelAnswerOrm, level: LevelOrm, training_id: int) -> AnswerRT:
    select_answer = None
    if level.messages[0].content_type == ContentType.POLL:
        options = [i.text for i in level.messages[0].poll.options]
        select_answer = options[it.answer_option_ids[0]]
    return AnswerRT(
        id=it.id,
        training_id=training_id,
        student_id=it.account_id,
        level_id=it.level_id,
        date=datetime.utcfromtimestamp(it.date_create),
        select_answer=select_answer,
        result=it.is_correct,
    )


def role_orm_to_role_data(it: RoleOrm, trainings: Optional[list[TrainingData]] = None,
                          accounts: Optional[list[AccountData]] = None) -> RoleData:
    return RoleData(
        id=it.id,
        name=it.name,
        date_create=it.date_create,
        trainings=trainings,
        accounts=accounts
    )


def level_answer_orm_to_level_answer_data(it: LevelAnswerOrm, level: Optional[LevelData] = None,
                                          student: Optional[StudentData] = None) -> LevelAnswerData:
    return LevelAnswerData(
        id=it.id,
        date_create=it.date_create,
        account_id=it.account_id,
        level_id=it.level_id,
        answer_option_ids=it.answer_option_ids,
        is_correct=it.is_correct,
        level=level,
        student=student,
    )
