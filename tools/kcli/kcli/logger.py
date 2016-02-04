import logging
from colorlog import ColoredFormatter


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

def get_logger(log_level=logging.WARNING):
    # Create stream handler with debug level
    sh = logging.StreamHandler()
    sh.setLevel(log_level)

    # Add the debug_formatter to sh
    sh.setFormatter(debug_formatter)

    # Create logger and add handler to it
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.addHandler(sh)

    return logger
