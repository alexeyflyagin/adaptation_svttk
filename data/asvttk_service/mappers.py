from typing import Optional

from data.asvttk_service.models import AccountOrm, RoleOrm, TrainingOrm, LevelOrm, LevelAnswerOrm
from data.asvttk_service.types import AccountData, RoleData, TrainingData, EmployeeData, StudentData, LevelData, \
    LevelAnswerData


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
