import inspect
import traceback
from datetime import datetime, timedelta
from time import time
from os import path, rename, remove, walk, mkdir, getenv
from sys import stdout, stderr
from threading import Thread
from typing import List, Dict, Any, Union, Optional, TextIO

from smdb_logger import LEVEL, COLOR


class Logger:
    __slots__ = (
        "log_file_name",
        "allowed",
        "log_to_console",
        "storage_life_extender_mode",
        "stored_logs",
        "max_caller_chain_size",
        "max_logfile_size",
        "max_logfile_lifetime",
        "out",
        "err",
        "use_caller_name",
        "use_file_names",
        "use_log_name",
        "header_used",
        "log_folder",
        "level_only_valid_for_console",
        "log_async",
        "log_disabled",
        "log_thread_count",
        "enable_file",
        "enable_color"
    )

    def __init__(
        self,
        /,
        log_file_name: Optional[str] = None,
        log_folder: str = ".",
        clear: bool = False,
        level: LEVEL = LEVEL.INFO,
        log_to_console: bool = True,
        storage_life_extender_mode: bool = False,
        max_caller_chain_size: int = -1,
        max_logfile_size: int = -1,
        max_logfile_lifetime: int = -1,
        out: TextIO = stdout,
        err: Optional[TextIO] = stderr,
        use_caller_name: bool = False,
        use_file_names: bool = True,
        use_log_name: bool = False,
        level_only_valid_for_console: bool = False,
        log_async: bool = False,
        log_disabled: bool = False,
        enable_file: bool = True,
        enable_color: bool = True,
    ) -> None:
        """
        Creates a logger with specific functions needed for server monitoring discord bot.
        :param log_file_name: (None): Log file name. If not provided, no file will be created.
        :param log_folder: ('.'): Absolute path to the log file's location
        :param clear: (False): Clear the (last used) log file from its contents
        :param level: (LEVEL.INFO): Sets the level of the logging done
        :param log_to_console: (True): Allows the logger to show logs in the console window if exists
        :param storage_life_extender_mode: (False): Stores the logs in memory instead of on storage media and only saves sometimes to preserve its lifetime
        :param max_caller_chain_size: (-1): Sets the maximum number of caller functions present in the log. It is set to -1 meaning no limit.
        :param max_logfile_size: (-1): Sets the maximum allowed log file size in MiB. By default, it's set to -1 meaning no limit.
        :param max_logfile_lifetime: (-1): Sets the maximum allowed log file life-time in Days. By default, it's set to -1 meaning no limit.
        :param out: (stdout): The standard output TextIO.
        :param err: (stderr): The standard error TextIO. If set to None 'out' will be used
        :param use_caller_name: (False): Allows the logger to use the caller functions name (with full call path) instead of the level. It only concerns logging to console.
        :param use_file_names: (True): Sets if the file name should be added to the beginning of the caller name. It only concerns logging to console.
        :param use_log_name: (False): Sets if the logger should include the file name's first part (split at the last '.'), to differentiate between multiple loggers on console only.
        :param level_only_valid_for_console: (False): Sets if the level set is only concerns the logging to console, or to file as well.
        :param log_disabled: (False): Disables logging, and disables warning message about no valid log destination
        :param enable_file: (True): Enables creating a logfile if a name is provided
        :param enable_color: (True): Enables colorization of the console log (NO_COLOR environment variable will overwrite it to False if set)
        """
        self.log_file_name = log_file_name
        self.validate_folder(log_folder)
        self.log_folder = log_folder
        self.allowed = LEVEL.get_hierarchy(level)
        self.storage_life_extender_mode = storage_life_extender_mode
        self.max_caller_chain_size = max_caller_chain_size
        self.stored_logs = []
        self.max_logfile_size = max_logfile_size
        self.max_logfile_lifetime = max_logfile_lifetime
        self.out = out if self.__is_valid_console(out) else None
        self.err = err if self.__is_valid_console(err) else self.out
        self.use_caller_name = use_caller_name
        self.use_file_names = use_file_names
        self.use_log_name = use_log_name
        self.header_used = False
        self.level_only_valid_for_console = level_only_valid_for_console
        self.log_async = log_async
        self.log_thread_count = 0
        self.log_disabled = log_disabled
        self.enable_file = enable_file
        self.enable_color = enable_color
        if getenv("NO_COLOR", False):
            self.enable_color = False
        if self.log_file_name is None and not log_to_console and not self.log_disabled:
            self.warning("Logger is not disabled, but 'log_file_name' is None, and 'log_to_console' are disabled!")
            self.warning("To disable this message, set 'log_disabled' to True")
        if clear and log_file_name is None:
            self.warning("Clear is set but 'log_file_name' is None!")
            self.warning("Can't clear if no file name is set!")
        if clear and log_file_name is not None:
            with open(path.join(log_folder, log_file_name), "w"):
                pass
        self.log_to_console = log_to_console and (self.out is not None and self.err is not None)

    def __get_date(self, timestamp: Optional[float] = None) -> datetime:
        if timestamp is None:
            timestamp = time()
        return datetime.fromtimestamp(timestamp)

    def __is_valid_console(self, console: Optional[TextIO]) -> bool:
        return console is not None and hasattr(console, "closed") and not console.closed and hasattr(console, "mode") and console.mode in ['w', 'W', 'a', 'A']

    def __check_logfile(self) -> None:
        if self.log_file_name is None: return
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
        if self.log_file_name is None: return []
        (dir_path, _, filenames) = walk(self.log_folder).__next__()
        return [path.join(dir_path, fname) for fname in filenames if self.log_file_name.split(".")[-1] in fname]

    def __log_to_file(self, log_msg: str, flush: bool = False) -> None:
        if self.log_file_name is None or not self.enable_file: return
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

    def __get_caller_chain(self):
        frames = inspect.getouterframes(inspect.currentframe().f_back.f_back, 3)
        should_add_filename = True
        caller = ""
        start = 0
        index = 0
        while index < len(frames):
            frame = frames[index]
            if path.basename(frame.filename) != "Logger.py":
                caller = frame.function
                start = index
                break
            index += 1
        previous_filename = path.basename(frames[start].filename)
        chain = []
        if caller == "<module>":
            chain.append(f"line {frames[start].lineno}")
        else:
            chain.append(caller)
            for frame in frames[start + 1:]:
                if path.basename(frame.filename) != previous_filename and self.use_file_names:
                    chain.append(previous_filename)
                    previous_filename = path.basename(frame.filename)
                    should_add_filename = False
                if self.max_caller_chain_size != -1 and len(chain) >= self.max_caller_chain_size:
                    break
                if frame.function in ["<module>", "_run_event", "_run_once", "_bootstrap_inner"] or path.basename(frame.filename) in ["threading.py"]:
                    break
                should_add_filename = True
                chain.append(frame.function)
        if self.use_file_names and should_add_filename:
            chain.append(previous_filename)
        return "->".join(reversed(chain))

    def __get_log_message(self, components: Dict[Any, str], level: LEVEL) -> str:
        string = ""
        if level != LEVEL.EXCEPTION:
            string += components[0]
            string += f" [{components['counter']}]"
            string += f" [{components[1]}]"
            string += f" [{components[3]}]"
        string += f": {components['data']}"
        return string.replace(' []', '').strip()

    def __log(self, level: LEVEL, data: str, counter: Union[str, None], end: str, only_console: bool) -> None:
        if level not in self.allowed and not self.level_only_valid_for_console: return
        if counter is None:
            counter = str(self.__get_date().strftime(r"%Y.%m.%d-%H:%M:%S"))
        log_components = {0: "", 1: "", "counter": counter, 3: level.value, "data": data}
        if self.header_used and level != LEVEL.HEADER:
            log_components[0] = "\t"
        if not only_console and (self.level_only_valid_for_console or level in self.allowed):
            self.__log_to_file(self.__get_log_message(log_components, level))
        if self.log_to_console and level in self.allowed and self.out is not None:
            if self.use_caller_name:
                caller = self.__get_caller_chain()
                log_components[3] = caller
            if self.use_log_name:
                name = '.'.join(self.log_file_name.split('.')[:-1])
                log_components[1] = name
            if only_console:
                log_components[3] = ""
            msg = f"{COLOR.from_level(level).value if self.enable_color else ''}{self.__get_log_message(log_components, level)}{COLOR.END.value if self.enable_color else ''}{end}"
            if level == LEVEL.ERROR:
                self.err.write(msg)
            else:
                self.out.write(msg)

    def __threaded_log(self, level: LEVEL, data: str, counter: str, end: str, only_console: bool) -> None:
        self.__log(level, data, counter, end, only_console)
        self.log_thread_count -= 1

    def __log_common(self, level: LEVEL, data: str, counter: Union[str, None], end: str, only_console: bool) -> None:
        if self.log_disabled: return
        if self.log_async:
            Thread(target=self.__threaded_log, args=[level, data, counter, end, only_console,], name=f"Async logging thread {self.log_thread_count}").start()
            self.log_thread_count += 1
        else:
            self.__log(level, data, counter, end, only_console)

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
            raise IOError("Argument `log_folder` can only refer to a directory!")

    def log(self, level: LEVEL, data: str, exception: Union[Exception, None] = None, counter: Union[str, None] = None, end: str = "\n", only_console: bool = False) -> None:
        """
        Creates a `level` logentry
        :param level: The level of the logentry
        :param data: The data to be logged
        :param exception: Exception thrown to be logged. If provided, an exception level log will follow.
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :param only_console: Flag if this should be saved to log-file or not (Default value is False)
        :return:
        """
        if level == LEVEL.INFO:
            self.info(data, counter, end, only_console)
        elif level == LEVEL.WARNING:
            self.warning(data, counter, end, only_console)
        elif level == LEVEL.ERROR:
            self.error(data, exception, counter, end, only_console)
        elif level == LEVEL.DEBUG:
            self.debug(data, counter, end, only_console)
        elif level == LEVEL.TRACE:
            self.trace(data, counter, end, only_console)
        else:
            self.header(data, counter, end, only_console)

    def header(self, data: str, counter: Union[str, None] = None, end: str = "\n", only_console: bool = False) -> None:
        """
        Creates a header
        :param data: Data to be shown
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :param only_console: Flag if this should be saved to log-file or not (Default value is False)
        :return:
        """
        self.__log_common(LEVEL.HEADER, f"{data:=^40}", counter, end, only_console)
        self.header_used = True

    def heartbeat(self, data: str, counter: Union[str, None] = None, end: str = "\n") -> None:
        """
        Only shows in console
        :param data: Data to be shown
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :return:
        """
        self.__log_common(LEVEL.TRACE, data, counter, end, only_console=True)

    def trace(self, data: str, counter: Union[str, None] = None, end: str = "\n", only_console: bool = False) -> None:
        """
        Creates a trace log
        :param data: Data to be shown
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :param only_console: Flag if this should be saved to log-file or not (Default value is False)
        :return:
        """
        self.__log_common(LEVEL.TRACE, data, counter, end, only_console)

    def debug(self, data: str, counter: Union[str, None] = None, end: str = "\n", only_console: bool = False) -> None:
        """
        Creates a debug log
        :param data: Data to be shown
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :param only_console: Flag if this should be saved to log-file or not (Default value is False)
        :return:
        """
        self.__log_common(LEVEL.DEBUG, data, counter, end, only_console)

    def warning(self, data: str, counter: Union[str, None] = None, end: str = "\n", only_console: bool = False) -> None:
        """
        Creates a warning log
        :param data: Data to be shown
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :param only_console: Flag if this should be saved to log-file or not (Default value is False)
        :return:
        """
        self.__log_common(LEVEL.WARNING, data, counter, end, only_console)

    def info(self, data: str, counter: Union[str, None] = None, end: str = "\n", only_console: bool = False) -> None:
        """
        Creates an info log
        :param data: Data to be shown
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :param only_console: Flag if this should be saved to log-file or not (Default value is False)
        :return:
        """
        self.__log_common(LEVEL.INFO, data, counter, end, only_console)

    def error(self, data: str, exception: Union[BaseException, None] = None, counter: Union[str, None] = None, end: str = "\n", only_console: bool = False) -> None:
        """
        Creates an error log
        :param data: Data to be shown
        :param exception: Exception thrown to be logged. If provided, an exception level log will follow.
        :param counter: Value unique to this print (Default is Date-Time in this format: %Y.%m.%d-%H:%M:%S)
        :param end: Value to be printed at last (Default is line-break)
        :param only_console: Flag if this should be saved to log-file or not (Default value is False)
        :return:
        """
        self.__log_common(LEVEL.ERROR, data, counter, end, only_console)
        if exception is not None: self.__log_common(LEVEL.EXCEPTION, ''.join(traceback.format_exception(None, exception, exception.__traceback__)), counter, end, False)

    def exception(self, exception: Exception) -> None:
        """
        Creates an exception log
        :param exception: The exception object to be logged
        :return:
        """
        self.__log_common(LEVEL.EXCEPTION, ''.join(traceback.format_exception(None, exception, exception.__traceback__)), None, "\n", False)
