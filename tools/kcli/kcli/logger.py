import logging
import sys
import traceback

from colorlog import ColoredFormatter

from exceptions import IRException

LOGGER_NAME = "IRLogger"
DEFAULT_LOGLEVEL = logging.WARNING

debug_formatter = ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(message)s",
    log_colors=dict(
        DEBUG='blue',
        INFO='green',
        WARNING='yellow',
        ERROR='red',
        CRITICAL='bold_red,bg_white',
    )
)


def kcli_traceback_handler(log):
    """Creates exception hook that sends IRException to log and other
    exceptions to stdout (default excepthook)
    :param log: logger to log trace
    """

    def my_excepthook(exc_type, exc_value, exc_traceback):
        # sends full exception with trace to log
        if not isinstance(exc_value, IRException):
            return sys.__excepthook__(exc_type, exc_value, exc_traceback)

        if log.getEffectiveLevel() <= logging.DEBUG:
            formated_exception = "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback))
            log.error(formated_exception + exc_value.msg)
        else:
            log.error(exc_value.msg)

    sys.excepthook = my_excepthook


LOG = logging.getLogger(LOGGER_NAME)
LOG.setLevel(DEFAULT_LOGLEVEL)

# Create stream handler with debug level
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)

# Add the debug_formatter to sh
sh.setFormatter(debug_formatter)

# Create logger and add handler to it
LOG.addHandler(sh)

kcli_traceback_handler(LOG)
