import logging
from colorlog import ColoredFormatter

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

LOG = logging.getLogger(LOGGER_NAME)
LOG.setLevel(DEFAULT_LOGLEVEL)

# Create stream handler with debug level
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)

# Add the debug_formatter to sh
sh.setFormatter(debug_formatter)

# Create logger and add handler to it
LOG.addHandler(sh)
