import dataclasses
from typing import Optional

from aiogram.types import Message

from data.asvttk_service.models import AccountType, LevelType


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
    message: list[Message]
    date_create: int
    date_start: Optional[int]
    date_end: Optional[int]
    students: Optional[list[AccountData]]
    levels: Optional[list["LevelData"]]

    @property
    def msg(self):
        return self.message[0]


@dataclasses.dataclass
class RoleData:
    id: int
    name: str
    date_create: int
    trainings: Optional[list[TrainingData]]
    accounts: Optional[list[AccountData]]


@dataclasses.dataclass
class EmployeeData(AccountData):
    roles: list[RoleData]


@dataclasses.dataclass
class StudentData(AccountData):
    training: TrainingData


@dataclasses.dataclass
class LevelData:
    id: int
    order: Optional[int]
    previous_level_id: int
    next_level_id: int
    training_id: int
    type: str
    date_create: int
    title: str
    messages: list[Message]
    training: Optional[TrainingData]

