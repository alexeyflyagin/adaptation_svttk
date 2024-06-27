import abc
import dataclasses
import os
from abc import ABC
from typing import Any, Optional

from openpyxl.styles import NamedStyle


@dataclasses.dataclass
class ReportFile:
    path: str
    filename: str

    @property
    def __absolute_path__(self):
        return rf'{self.path}\{self.filename}'

    def delete(self):
        os.remove(self.__absolute_path__)


class ColumnConverter(ABC):
    @abc.abstractmethod
    def convert(self, v: Optional[Any]) -> Any:
        pass


class ColumnRT:
    def __init__(self, alias: Optional[str] = None, style: Optional[NamedStyle] = None,
                 converter: Optional[ColumnConverter] = None, width: float = 8.0):
        self.alias = alias
        self.style = style
        self.converter = converter
        self.width = width


@dataclasses.dataclass
class ReportTable:
    __tablename__ = "default"
    __columns__ = {}

    @property
    def __aliases__(self) -> list[str]:
        return [v.alias if v.alias else k for k, v in self.__columns__.items()]

    @property
    def __named_styles__(self) -> list[NamedStyle]:
        return [i.style for i in self.__columns__.values()]

    @property
    def __values__(self):
        return list(dataclasses.asdict(self).values())

    @property
    def __values_converted__(self):
        columns = list(self.__columns__.values())
        values = list(dataclasses.asdict(self).values())
        if len(columns) != len(values):
            raise ValueError("len(columns) != len(values)")
        res = []
        for i in range(len(values)):
            if columns[i].converter:
                res.append(columns[i].converter.convert(values[i]))
            else:
                res.append(values[i])
        return res
