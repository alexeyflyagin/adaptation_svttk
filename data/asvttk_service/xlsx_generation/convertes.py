from datetime import datetime
from enum import Enum
from typing import Optional, Any

from data.asvttk_service.xlsx_generation.types import ColumnConverter


class LIST(ColumnConverter):
    def __init__(self, sep: str = ", "):
        self.sep = sep

    def convert(self, v: Optional[list[Any]]) -> Any:
        if v is None:
            return v
        return self.sep.join(map(str, v))


class MSKDATE(ColumnConverter):
    def __init__(self, sep: str = ", "):
        self.sep = sep

    def convert(self, v: Optional[datetime]) -> Any:
        if v is None:
            return v
        return datetime.fromtimestamp(v.timestamp() + 3 * 3600)


class ENUM(ColumnConverter):

    def convert(self, v: Optional[Enum]) -> Any:
        if v is None:
            return v
        return str(v.value)
