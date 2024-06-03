import dataclasses
from typing import Optional

from data.asvttk_service.models import AccountType


@dataclasses.dataclass
class LogInData:
    token: str
    is_first: bool
    access_key: str
    account_type: AccountType
    account_id: int


@dataclasses.dataclass
class GiveUpAccountData:
    new_access_key: str


@dataclasses.dataclass
class CreatedAccountData:
    account_id: int
    access_key: str


@dataclasses.dataclass
class CreatedRoleData:
    role_id: int


@dataclasses.dataclass
class CreatedTrainingData:
    training_id: int


@dataclasses.dataclass
class AccountData:
    id: int
    type: AccountType
    email: Optional[str]
    date_create: int
    first_name: str
    last_name: Optional[str]
    patronymic: Optional[str]
    training_id: Optional[int]
    date_complete_training: Optional[int]


@dataclasses.dataclass
class TrainingData:
    id: int
    name: str
    start_text: str
    html_start_text: str
    photo_id: Optional[str]
    date_create: int
    date_start: Optional[int]
    date_end: Optional[int]


@dataclasses.dataclass
class RoleData:
    id: int
    name: str
    date_create: int
    trainings: Optional[list[TrainingData]]
    accounts: Optional[list[AccountData]]
