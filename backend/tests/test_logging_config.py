import importlib
import sys
import types

def test_init_logging_with_json_logger():
    class DummyFormatter:
        def __init__(self, *args, **kwargs):
            pass

    jsonlogger_module = types.SimpleNamespace(JsonFormatter=DummyFormatter)
    fake_pkg = types.SimpleNamespace(jsonlogger=jsonlogger_module)
    sys.modules["pythonjsonlogger"] = fake_pkg
    sys.modules["pythonjsonlogger.jsonlogger"] = jsonlogger_module

    import backend.logging_config as logging_config

    try:
        importlib.reload(logging_config)
        logging_config.init_logging()
        assert logging_config.HAS_JSON_LOGGER is True
    finally:
        sys.modules.pop("pythonjsonlogger", None)
        importlib.reload(logging_config)