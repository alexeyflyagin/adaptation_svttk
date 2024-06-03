from data.asvttk_service.models import AccountOrm
from data.asvttk_service.types import AccountData


def account_orm_to_account_data(account_orm: AccountOrm) -> AccountData:
    return AccountData(
        id=account_orm.id,
        type=account_orm.type,
        email=account_orm.email,
        date_create=account_orm.date_create,
        first_name=account_orm.first_name,
        last_name=account_orm.last_name,
        patronymic=account_orm.patronymic,
        training_id=account_orm.training_id,
        date_complete_training=account_orm.date_complete_training
    )
