from typing import Optional

from data.asvttk_service.models import AccountOrm, RoleOrm, TrainingOrm
from data.asvttk_service.types import AccountData, RoleData, TrainingData


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


def training_orm_to_training_data(it: TrainingOrm) -> TrainingData:
    return TrainingData(
        id=it.id,
        name=it.name,
        start_text=it.start_text,
        html_start_text=it.html_start_text,
        photo_id=it.photo_id,
        date_create=it.date_create,
        date_start=it.date_start,
        date_end=it.date_end,
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
