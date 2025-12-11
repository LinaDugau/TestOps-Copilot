from unittest.mock import Mock, patch
import backend.gitlab_client  
from backend.gitlab_client import commit_code, fetch_defects
import gitlab.exceptions

backend.gitlab_client.logger.info("Module loaded for coverage")

def test_commit_code_creates_file_and_branch():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_project = Mock()
        def raise_get_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabGetError("Not found")
        
        mock_project.branches.get.side_effect = raise_get_error
        mock_project.branches.create.return_value = None
        mock_project.files.get.side_effect = raise_get_error
        mock_project.files.create.return_value = None
        mock_project.commits.list.return_value = [Mock(id="abc123")]
        mock_project.default_branch = "main"

        mock_gl.return_value.projects.get.return_value = mock_project
        mock_gl.return_value.auth.return_value = None

        result = commit_code(
            repo_id=12345,
            branch="feature/tests",
            file_path="tests/auto_api.py",
            content="import pytest\n\ndef test_x(): pass",
            commit_message="Add generated tests"
        )

        assert result["success"] is True
        assert "создан" in result["message"]
        assert result["commit_sha"] == "abc123"


def test_commit_code_updates_existing_file():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_project = Mock()
        mock_file = Mock()
        mock_file.save.return_value = None
        mock_project.files.get.return_value = mock_file
        mock_project.commits.list.return_value = [Mock(id="abc123")]

        mock_gl.return_value.projects.get.return_value = mock_project
        mock_gl.return_value.auth.return_value = None

        result = commit_code(
            repo_id="group/project",
            branch="main",
            file_path="existing.py",
            content="updated content"
        )

        assert result["success"] is True
        assert "обновлён" in result["message"]


def test_fetch_defects():
    with patch("backend.gitlab_client.settings") as mock_settings, \
         patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_settings.GITLAB_URL = "https://gitlab.example.com"
        mock_settings.GITLAB_TOKEN = "token"

        mock_project = Mock()
        mock_issue = Mock(
            iid=123,
            title="UI Bug",
            description="Crash on mobile",
            labels=["bug"],
            state="opened",
            created_at=None
        )
        mock_project.issues.list.return_value = [mock_issue]
        mock_gl.return_value.projects.get.return_value = mock_project
        mock_gl.return_value.auth.return_value = None

        defects = fetch_defects(repo_id=12345, labels=["bug"], max_issues=1)
        assert defects["success"] is True
        assert defects["count"] == 1
        assert defects["issues"][0]["title"] == "UI Bug"
        assert defects["issues"][0]["id"] == 123


def test_commit_code_missing_gitlab_settings():
    with patch("backend.gitlab_client.settings") as mock_settings:
        mock_settings.GITLAB_URL = None
        mock_settings.GITLAB_TOKEN = None

        result = commit_code(repo_id=123, branch="main", file_path="x.py", content="code")

        assert result["success"] is False
        assert "GitLab не настроен" in result["message"]


def test_commit_code_auth_error():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        def raise_auth_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabAuthenticationError("Invalid token")

        mock_gl.return_value.auth.side_effect = raise_auth_error

        result = commit_code(repo_id=12345, branch="main", file_path="test.py", content="code")

        assert result["success"] is False
        assert "Ошибка аутентификации в GitLab" in result["message"]
        assert "Проверьте GITLAB_TOKEN" in result["message"]


def test_commit_code_project_not_found():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        def raise_project_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabGetError("404 Project Not Found")

        mock_gl.return_value.projects.get.side_effect = raise_project_error

        result = commit_code(repo_id=99999, branch="main", file_path="test.py", content="code")

        assert result["success"] is False
        assert "Репозиторий с ID '99999' не найден" in result["message"]


def test_commit_code_branch_create_fail():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_project = Mock()
        def raise_get_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabGetError("Not found")
        mock_project.branches.get.side_effect = raise_get_error
        def raise_create_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabCreateError("500 Branch creation failed")
        mock_project.branches.create.side_effect = raise_create_error
        mock_gl.return_value.projects.get.return_value = mock_project
        mock_gl.return_value.auth.return_value = None

        result = commit_code(repo_id=12345, branch="fail-branch", file_path="test.py", content="code")

        assert result["success"] is False
        assert "Не удалось создать ветку fail-branch" in result["message"]


def test_commit_code_file_create_fail():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_project = Mock()
        def raise_get_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabGetError("Not found")
        mock_project.branches.get.side_effect = raise_get_error
        mock_project.branches.create.return_value = None
        mock_project.files.get.side_effect = raise_get_error
        def raise_create_file_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabCreateError("File creation failed")
        mock_project.files.create.side_effect = raise_create_file_error
        mock_gl.return_value.projects.get.return_value = mock_project
        mock_gl.return_value.auth.return_value = None

        result = commit_code(repo_id=12345, branch="main", file_path="new_fail.py", content="code")

        assert result["success"] is False
        assert "Не удалось создать файл new_fail.py" in result["message"]


def test_commit_code_file_update_fail():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_project = Mock()
        mock_file = Mock()
        mock_project.files.get.return_value = mock_file
        mock_file.save.side_effect = gitlab.exceptions.GitlabUpdateError("Update failed")
        mock_gl.return_value.projects.get.return_value = mock_project
        mock_gl.return_value.auth.return_value = None

        result = commit_code(repo_id=12345, branch="main", file_path="update_fail.py", content="code")

        assert result["success"] is False
        assert "Ошибка при работе с файлом" in result["message"]


def test_commit_code_forbidden_access():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        def raise_project_error(*args, **kwargs):
            raise gitlab.exceptions.GitlabGetError("403 Forbidden")

        mock_gl.return_value.projects.get.side_effect = raise_project_error
        mock_gl.return_value.auth.return_value = None

        result = commit_code(repo_id="group/proj", branch="main", file_path="x.py", content="code")

        assert result["success"] is False
        assert "Нет доступа" in result["message"]


def test_commit_code_http_error():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_gl.return_value.projects.get.side_effect = gitlab.exceptions.GitlabHttpError("500")
        mock_gl.return_value.auth.return_value = None

        result = commit_code(repo_id="group/proj", branch="main", file_path="x.py", content="code")

        assert result["success"] is False
        assert "HTTP ошибка" in result["message"]


def test_commit_code_auth_error_outer():
    with patch("backend.gitlab_client.settings") as mock_settings, \
         patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_settings.GITLAB_URL = "https://gitlab.local"
        mock_settings.GITLAB_TOKEN = "token"
        mock_gl.side_effect = gitlab.exceptions.GitlabAuthenticationError("bad token")

        result = commit_code(repo_id=1, branch="main", file_path="x.py", content="code")

        assert result["success"] is False
        assert "Проверьте GITLAB_TOKEN" in result["message"]


def test_commit_code_unexpected_error():
    with patch("backend.gitlab_client.settings") as mock_settings, \
         patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_settings.GITLAB_URL = "https://gitlab.local"
        mock_settings.GITLAB_TOKEN = "token"
        mock_gl.side_effect = ValueError("boom")

        result = commit_code(repo_id=1, branch="main", file_path="x.py", content="code")

        assert result["success"] is False
        assert "Неожиданная ошибка" in result["message"]


def test_fetch_defects_fallback_without_labels():
    with patch("backend.gitlab_client.settings") as mock_settings, \
         patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_settings.GITLAB_URL = "https://gitlab.local"
        mock_settings.GITLAB_TOKEN = "token"

        mock_issue = Mock()
        mock_issue.iid = 5
        mock_issue.id = 5
        mock_issue.title = "No labels"
        mock_issue.description = "desc"
        mock_issue.labels = []
        mock_issue.state = "opened"
        mock_issue.created_at = None
        mock_issue.assignees = []

        project = Mock()

        def issues_list_side_effect(*args, **kwargs):
            if kwargs.get("labels"):
                return []
            return [mock_issue]

        project.issues.list.side_effect = issues_list_side_effect
        mock_gl.return_value.projects.get.return_value = project
        mock_gl.return_value.auth.return_value = None

        res = fetch_defects(repo_id=123, labels=["bug"], max_issues=1)

        assert res["success"] is True
        assert res["count"] == 1
        assert res["issues"][0]["fallback"] is True


def test_fetch_defects_not_configured():
    with patch("backend.gitlab_client.settings") as mock_settings:
        mock_settings.GITLAB_URL = None
        mock_settings.GITLAB_TOKEN = None

        res = fetch_defects(repo_id=1, labels=["bug"])
        assert res["success"] is False
        assert res["count"] == 0
        assert "GitLab не настроен" in res["message"]


def test_fetch_defects_http_error():
    with patch("backend.gitlab_client.settings") as mock_settings, \
         patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_settings.GITLAB_URL = "https://gitlab.local"
        mock_settings.GITLAB_TOKEN = "token"
        mock_gl.return_value.auth.return_value = None
        mock_gl.return_value.projects.get.side_effect = gitlab.exceptions.GitlabGetError("boom")

        res = fetch_defects(repo_id=1, labels=["bug"])
        assert res["success"] is False
        assert res["message"] == "boom"


def test_fetch_defects_unexpected_error():
    with patch("backend.gitlab_client.settings") as mock_settings, \
         patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_settings.GITLAB_URL = "https://gitlab.local"
        mock_settings.GITLAB_TOKEN = "token"
        mock_gl.side_effect = ValueError("crash")

        res = fetch_defects(repo_id=1, labels=["bug"])
        assert res["success"] is False
        assert "crash" in res["message"]


def test_commit_code_project_error_other():
    with patch("backend.gitlab_client.gitlab.Gitlab") as mock_gl:
        mock_gl.return_value.auth.return_value = None
        mock_gl.return_value.projects.get.side_effect = gitlab.exceptions.GitlabGetError("timeout")

        result = commit_code(repo_id=999, branch="main", file_path="x.py", content="code")
        assert result["success"] is False
        assert "Не удалось получить доступ" in result["message"]