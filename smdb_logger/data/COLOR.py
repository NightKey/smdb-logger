from enum import Enum

from smdb_logger.data import LEVEL


class COLOR(Enum):
    INFO = "\033[92m"
    ERROR = "\033[91m"
    WARNING = "\033[93m"
    HEADER = "\033[94m"
    DEBUG = "\033[95m"
    TRACE = "\033[96m"
    END = "\033[0m"

    @staticmethod
    def from_level(level: LEVEL) -> "COLOR":
        return getattr(COLOR, level.value)

