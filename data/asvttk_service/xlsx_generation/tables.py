import dataclasses
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from openpyxl.styles import NamedStyle

from data.asvttk_service.xlsx_generation.convertes import ENUM, LIST, MSKDATE
from data.asvttk_service.xlsx_generation.types import ReportTable, ColumnRT, ColumnConverter

PERCENT_STYLE = NamedStyle(name="percent_style", number_format="0.00%")
DATE_STYLE = NamedStyle(name="date_style", number_format="DD.MM.YY hh:mm:ss")


COLUMN_WIDTH_DATE = 20.0
COLUMN_WIDTH_ID = 4.0
COLUMN_WIDTH_NUM = 10.0
COLUMN_WIDTH_F_ID = 12.0
COLUMN_WIDTH_NAME = 20.0
COLUMN_WIDTH_TITLE = 30.0
COLUMN_WIDTH_TEXT = 50.0
COLUMN_WIDTH_SMALL_TEXT = 30.0
COLUMN_WIDTH_SMALL_LIST = 30.0


class RStudentState(Enum):
    CREATED = "СОЗДАНО"
    LEARNING = "ОБУЧЕНИЕ"
    COMPLETED = "ЗАВЕРШЕНО"


class RTrainingState(Enum):
    ACTIVE = "АКТИВНЫЙ"
    INACTIVE = "НЕАКТИВНЫЙ"


class RLevelType(Enum):
    CONTROL = "КОНТРОЛЬ"
    INFO = "ИНФОРМАЦИЯ"


class ResultConverter(ColumnConverter):

    RESULT_TRUE = "ВЕРНО"
    RESULT_FALSE = "НЕВЕРНО"

    def convert(self, v: Optional[Any]) -> Any:
        if v is None:
            return v
        return self.RESULT_TRUE if v else self.RESULT_FALSE


@dataclasses.dataclass
class StudentRT(ReportTable):
    __tablename__ = "Ученики"

    id: int
    first_name: str
    last_name: str
    patronymic: str
    date_create: datetime
    state: RStudentState
    progress: float

    __columns__ = {
        "id": ColumnRT("ID", width=COLUMN_WIDTH_ID),
        "first_name": ColumnRT("Имя", width=COLUMN_WIDTH_NAME),
        "last_name": ColumnRT("Фамилия", width=COLUMN_WIDTH_NAME),
        "patronymic": ColumnRT("Отчество", width=COLUMN_WIDTH_NAME),
        "date_create": ColumnRT("Дата создания", converter=MSKDATE(), style=DATE_STYLE, width=COLUMN_WIDTH_DATE),
        "state": ColumnRT("Состояние", converter=ENUM(), width=COLUMN_WIDTH_NAME),
        "progress": ColumnRT("Прогресс", style=PERCENT_STYLE, width=COLUMN_WIDTH_NUM),
    }


@dataclasses.dataclass
class AnswerRT(ReportTable):
    __tablename__ = "Ответы"

    id: int
    training_id: int
    student_id: int
    level_id: int
    date: datetime
    select_answer: str
    result: bool

    __columns__ = {
        "id": ColumnRT("ID", width=COLUMN_WIDTH_ID),
        "training_id": ColumnRT("ID Курса", width=COLUMN_WIDTH_F_ID),
        "student_id": ColumnRT("ID Ученика", width=COLUMN_WIDTH_F_ID),
        "level_id": ColumnRT("ID Уровня", width=COLUMN_WIDTH_F_ID),
        "date": ColumnRT("Дата", converter=MSKDATE(), style=DATE_STYLE, width=COLUMN_WIDTH_DATE),
        "select_answer": ColumnRT("Выбранный ответ", width=COLUMN_WIDTH_SMALL_LIST),
        "result": ColumnRT("Результат", converter=ResultConverter(), style=PERCENT_STYLE, width=COLUMN_WIDTH_NAME),
    }


@dataclasses.dataclass
class LevelRT(ReportTable):
    __tablename__ = "Уровни"

    id: int
    num: int
    level_type: RLevelType
    date_create: datetime
    title: str
    text: Optional[str]
    content_type: str
    file_count: int
    options: Optional[list[str]]
    correct_option: Optional[str]
    explanation: Optional[str]

    __columns__ = {
        "id": ColumnRT("ID", width=COLUMN_WIDTH_ID),
        "num": ColumnRT("Номер", width=COLUMN_WIDTH_NUM),
        "level_type": ColumnRT("Тип уровня", converter=ENUM(), width=COLUMN_WIDTH_NAME),
        "date_create": ColumnRT("Дата создания", converter=MSKDATE(), style=DATE_STYLE, width=COLUMN_WIDTH_DATE),
        "title": ColumnRT("Заголовок", width=COLUMN_WIDTH_TITLE),
        "text": ColumnRT("Текст", width=COLUMN_WIDTH_TEXT),
        "content_type": ColumnRT("Тип контента", width=COLUMN_WIDTH_NAME),
        "file_count": ColumnRT("Файлов", width=COLUMN_WIDTH_NUM),
        "options": ColumnRT("Варианты ответов", converter=LIST(), width=COLUMN_WIDTH_SMALL_LIST),
        "correct_option": ColumnRT("Верный ответ", width=COLUMN_WIDTH_NAME),
        "explanation": ColumnRT("Объяснение", width=COLUMN_WIDTH_SMALL_TEXT),
    }


@dataclasses.dataclass
class TrainingRT(ReportTable):
    __tablename__ = "Курсы"

    id: int
    name: str
    start_msg: str
    date_create: datetime
    state: RTrainingState
    date_start: Optional[datetime]
    date_complete: Optional[datetime]

    __columns__ = {
        "id": ColumnRT("ID", width=COLUMN_WIDTH_ID),
        "name": ColumnRT("Название", width=COLUMN_WIDTH_NAME),
        "start_msg": ColumnRT("Начальное сообщение", width=COLUMN_WIDTH_TEXT),
        "date_create": ColumnRT("Дата создания", converter=MSKDATE(), style=DATE_STYLE, width=COLUMN_WIDTH_DATE),
        "state": ColumnRT("Состояние", converter=ENUM(), width=COLUMN_WIDTH_NAME),
        "date_start": ColumnRT("Дата запуска", converter=MSKDATE(), style=DATE_STYLE, width=COLUMN_WIDTH_DATE),
        "date_complete": ColumnRT("Дата остановки", converter=MSKDATE(), style=DATE_STYLE, width=COLUMN_WIDTH_DATE),
    }


@dataclasses.dataclass
class ReportRT(ReportTable):
    __tablename__ = "Отчет"

    date_create: datetime

    __columns__ = {
        "date_create": ColumnRT("Дата создания", converter=MSKDATE(), style=DATE_STYLE, width=COLUMN_WIDTH_DATE),
    }
