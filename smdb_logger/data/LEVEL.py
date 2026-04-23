from enum import Enum
from typing import List


class LEVEL(Enum):
    WARNING = "WARNING"
    INFO = "INFO"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    TRACE = "TRACE"
    HEADER = "HEADER"

    @staticmethod
    def from_string(string: str) -> 'LEVEL':
        for lvl in [LEVEL.DEBUG, LEVEL.INFO, LEVEL.WARNING, LEVEL.ERROR, LEVEL.HEADER]:
            if lvl.value.lower() == string.lower():
                return lvl
        return None

    @staticmethod
    def get_hierarchy(selected: 'LEVEL') -> List['LEVEL']:
        tmp = [LEVEL.TRACE, LEVEL.DEBUG, LEVEL.INFO,
               LEVEL.WARNING, LEVEL.ERROR, LEVEL.HEADER]
        if isinstance(selected, str):
            selected = LEVEL.from_string(selected)
        return tmp[tmp.index(selected):]

