from datetime import timedelta, datetime
from time import time
import inspect
from typing import Callable, List, Dict, Any
from enum import Enum
from os import path, rename, walk, remove, mkdir
from sys import stdout, stderr
from shutil import move


class LEVEL(Enum):
    WARNING = "WARNING"
    INFO = "INFO"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    TRACE = "TRACE"
    HEADER = "HEADER"

    def from_string(string: str) -> 'LEVEL':
        for lvl in [LEVEL.DEBUG, LEVEL.INFO, LEVEL.WARNING, LEVEL.ERROR, LEVEL.HEADER]:
            if lvl.value.lower() == string.lower():
                return lvl
        return None

    def get_hierarchy(selected: 'LEVEL') -> List['LEVEL']:
        tmp = [LEVEL.TRACE, LEVEL.DEBUG, LEVEL.INFO,
               LEVEL.WARNING, LEVEL.ERROR, LEVEL.HEADER]
        if isinstance(selected, str):
            selected = LEVEL.from_string(selected)
        return tmp[tmp.index(selected):]


class COLOR(Enum):
    INFO = "\033[92m"
    ERROR = "\033[91m"
    WARNING = "\033[93m"
    HEADER = "\033[94m"
    DEBUG = "\033[95m"
    TRACE = "\033[96m"
    END = "\033[0m"

    def from_level(level: LEVEL) -> "COLOR":
        return getattr(COLOR, level.value)


class Logger:
    __slots__ = "log_file_name", "allowed", "log_to_console", "storage_life_extender_mode", "stored_logs", "max_logfile_size", "max_logfile_lifetime", "__print", "__error", "use_caller_name", "use_file_names", "use_log_name", "header_used", "log_folder", "level_only_valid_for_console", "log_disabled"

    def __init__(
        self,
        log_file_name: str = None,
        log_folder: str = ".",
        clear: bool = False,
        level: LEVEL = LEVEL.INFO,
        log_to_console: bool = True,
        storage_life_extender_mode: bool = False,
        max_logfile_size: int = -1,
        max_logfile_lifetime: int = -1,
        __print: Callable = stdout.write,
        __error: Callable = stderr.write,
        use_caller_name: bool = False,
        use_file_names: bool = True,
        use_log_name: bool = False,
        level_only_valid_for_console: bool = False,
        log_disabled: bool = False
    ) -> None:
        """
        Creates a logger with specific functions needed for server monitoring discord bot.
        log_file_name (None): Log file name
        log_folder ('.'): Absoluth path to the log file's location
        clear (False): Clear the (last used) log file from it's contents
        level (LEVEL.INFO): Sets the level of the logging done
        log_to_console (True): Allows the logger to show logs in the console window if exists
        storage_life_extender_mode (False): Stores the logs in memory instead of on storage media and only saves sometimes to preserve it's lifetime
        max_logfile_size (-1): Sets the maximum allowed log file size in MiB. By default it's set to -1 meaning no limit.
        max_logfile_lifetime (-1): Sets the maximum allowed log file life time in Days. By default it's set to -1 meaning no limit.
        __print (stdout.write): The function to use to log to console.
        __error (stderr.write): The function to use to log errors to console. If set to None __print will be used
        use_caller_name (False): Allows the logger to use the caller functions name (with full call path) instead of the level. It only concerns logging to console.
        use_file_names (True): Sets if the file name should be added to the begining of the caller name. It only concerns logging to console.
        use_log_name (False): Sets if the logger should include the file name name's first part (split at the last '.'), to differenciate between multiple loggers on console only.
        level_only_valid_for_console (False): Sets if the level set is only concerns the logging to console, or to file as well.
        log_disabled (False): Disables logging, and disables warning message about no valid log destination
        """
        self.log_file_name = log_file_name
        self.validate_folder(log_folder)
        self.log_folder = log_folder
        self.allowed = LEVEL.get_hierarchy(level)
        self.log_to_console = log_to_console
        self.storage_life_extender_mode = storage_life_extender_mode
        self.stored_logs = []
        self.max_logfile_size = max_logfile_size
        self.max_logfile_lifetime = max_logfile_lifetime
        self.__print = __print
        self.__error = __error if __error is not None else __print
        self.use_caller_name = use_caller_name
        self.use_file_names = use_file_names
        self.use_log_name = use_log_name
        self.header_used = False
        self.level_only_valid_for_console = level_only_valid_for_console
        self.log_disabled = log_disabled
        if self.log_file_name is None and not self.log_to_console and not self.log_disabled:
            self.log_to_console = True
            self.warning("Logger is not disabled, but 'log_file_name' is None, and 'log_to_console' are disabled!")
            self.warning("To disable this message, set 'log_disabled' to True")
            self.log_to_console = False
        if clear:
            with open(path.join(log_folder, log_file_name), "w"):
                pass

    def __get_date(self, timestamp: float = None) -> datetime:
        if timestamp is None:
            timestamp = time()
        return datetime.fromtimestamp(timestamp)

    def __check_logfile(self) -> None:
        if self.max_logfile_size != -1 and path.exists(path.join(self.log_folder, self.log_file_name)) and (path.getsize(path.join(self.log_folder, self.log_file_name)) / (1024 ^ 2)) > self.max_logfile_size:
            tmp = self.log_file_name.split(".")
            tmp[0] += str(self.__get_date().strftime(r"%y.%m.%d-%I"))
            new_name = ".".join(tmp)
            rename(path.join(self.log_folder, self.log_file_name),
                   path.join(self.log_folder, new_name))
            with open(path.join(self.log_folder, self.log_file_name), "w") as f:
                pass

        if self.max_logfile_lifetime != -1:
            names = self.__get_all_logfile_names()
            for name in names:
                if name != self.log_file_name and self.__get_date() - self.__get_date(path.getctime(name)) > timedelta(days=self.max_logfile_lifetime):
                    remove(name)

    def __get_all_logfile_names(self) -> List[str]:
        for dir_path, _, filenames in walk(self.log_folder):
            return [path.join(dir_path, fname) for fname in filenames if self.log_file_name.split(".")[-1] in fname]

    def __log_to_file(self, log_msg: str, flush: bool = False) -> None:
        if self.log_file_name is None: return
        if self.storage_life_extender_mode:
            self.stored_logs.append(log_msg)
        else:
            with open(path.join(self.log_folder, self.log_file_name), "a", encoding="UTF-8") as f:
                f.write(log_msg)
                f.write("\n")
        if len(self.stored_logs) > 500 or flush:
            if log_msg == "":
                del self.stored_logs[-1]
            with open(path.join(self.log_folder, self.log_file_name), "a", encoding="UTF-8") as f:
                f.write("\n".join(self.stored_logs))
                self.stored_logs = []
        self.__check_logfile()

    def __get_caller_name(self):
        frames = inspect.getouterframes(
            inspect.currentframe().f_back.f_back, 2)
        caller = f"{frames[1].function if frames[1].function != 'log' else frames[2].function}"
        start = 3 if frames[1].function == "log" else 2
        previous_filename = path.basename(frames[start-1].filename)
        if caller == "<module>":
            return previous_filename
        for frame in frames[start:]:
            if frame.function in ["<module>", "_run_event", "_run_once", "_bootstrap_inner"] or path.basename(frame.filename) in ["threading.py"]:
                break
            if path.basename(frame.filename) != previous_filename and self.use_file_names:
                caller = f"{frame.function}->{previous_filename}->{caller}"
                previous_filename = path.basename(frame.filename)
            else:
                caller = f"{frame.function}->{caller}"
        return f"{previous_filename}->{caller}" if self.use_file_names else caller

    def __get_log_message(self, components: Dict[Any, str]) -> str:
        string = components[0]
        string += f" [{components['counter']}]"
        string += f" [{components[1]}]"
        string += f" [{components[3]}]"
        string += f": {components['data']}"
        return string.replace(' []', '').strip()

    def __log(self, level: LEVEL, data: str, counter: str, end: str) -> None:
        if self.log_disabled: return
        if counter is None:
            counter = str(self.__get_date().strftime(r"%Y.%m.%d-%H:%M:%S"))
        log_components = {0: "", 1: "", "counter": counter, 3: level, "data": data}
        if self.header_used and level != LEVEL.HEADER:
            log_components[0] = "\t"
        if self.level_only_valid_for_console or level in self.allowed:
            self.__log_to_file(self.__get_log_message(log_components))
        if self.log_to_console and level in self.allowed and level is not LEVEL.HEADER:
            if self.use_caller_name:
                caller = self.__get_caller_name()
                log_components[3] = caller
            if self.use_log_name:
                name = '.'.join(self.log_file_name.split('.')[:-1])
                log_components[1] = name
            msg = f"{COLOR.from_level(level).value}{self.__get_log_message(log_components)}{COLOR.END.value}{end}"
            if level == LEVEL.ERROR:
                self.__error(msg)
            else:
                self.__print(msg)

    def get_buffer(self) -> List[str]:
        return self.stored_logs if self.storage_life_extender_mode else []

    def flush_buffer(self):
        if self.storage_life_extender_mode:
            self.__log_to_file("", True)

    def set_level(self, level: LEVEL) -> None:
        self.allowed = LEVEL.get_hierarchy(level)

    def set_folder(self, folder: str) -> None:
        self.validate_folder(folder)
        self.log_folder = folder

    def validate_folder(self, log_folder: str) -> None:
        if not path.exists(log_folder):
            if "/" not in log_folder or "\\" not in log_folder:
                log_folder = path.join(path.curdir, log_folder)
            mkdir(log_folder)
        elif not path.isdir(log_folder):
            raise IOError(
                "Argument `log_folder` can only reffer to a directory!")

    def log(self, level: LEVEL, data: str, counter: str = None, end: str = "\n") -> None:
        if level == LEVEL.INFO:
            self.info(data, counter, end)
        elif level == LEVEL.WARNING:
            self.warning(data, counter, end)
        elif level == LEVEL.ERROR:
            self.error(data, counter, end)
        elif level == LEVEL.DEBUG:
            self.debug(data, counter, end)
        elif level == LEVEL.TRACE:
            self.trace(data, counter, end)
        else:
            self.header(data, counter, end)

    def header(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.HEADER, f"{data:=^40}", counter, end)
        self.header_used = True

    def trace(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.TRACE, data, counter, end)

    def debug(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.DEBUG, data, counter, end)

    def warning(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.WARNING, data, counter, end)

    def info(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.INFO, data, counter, end)

    def error(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.ERROR, data, counter, end)
