import logging
from colorlog import ColoredFormatter

LOGER_NAME = "IRLogger"
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

LOG = logging.getLogger(LOGER_NAME)
LOG.setLevel(DEFAULT_LOGLEVEL)

# def init_logger(log_level=logging.WARNING):
# Create stream handler with debug level
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)

# Add the debug_formatter to sh
sh.setFormatter(debug_formatter)

# Create logger and add handler to it
LOG.addHandler(sh)
