import logging
import logging.config

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


def init_logging() -> None:
    if HAS_JSON_LOGGER:
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": jsonlogger.JsonFormatter,
                    "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d %(process)d %(thread)d"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "level": "INFO",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": "INFO"
            }
        }
    else:
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": "INFO",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": "INFO"
            }
        }

    logging.config.dictConfig(logging_config)