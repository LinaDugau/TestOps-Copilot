import importlib
import sys
from pathlib import Path


def test_conftest_inserts_project_root(monkeypatch):
    """Проверяем, что conftest добавляет корень проекта в sys.path при загрузке."""
    project_root = Path(__file__).resolve().parents[2]  
    new_path = [p for p in sys.path if str(project_root) not in p]
    monkeypatch.setattr(sys, "path", new_path)

    import backend.conftest as conf
    importlib.reload(conf)

    normalized = {str(Path(p).resolve()) for p in sys.path}
    assert str(project_root.resolve()) in normalized