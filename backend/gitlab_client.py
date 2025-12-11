import logging
import gitlab
from typing import Dict, Any, List

try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger("app")


def commit_code(
    repo_id: int | str,
    branch: str,
    file_path: str,
    content: str,
    commit_message: str = "Generated tests from TestOps Copilot"
) -> Dict[str, Any]:
    """
    Коммитит код в GitLab репозиторий.
    
    Args:
        repo_id: ID репозитория в GitLab
        branch: Название ветки (по умолчанию 'main')
        file_path: Путь к файлу в репозитории (например, 'tests/manual_ui_tests.py')
        content: Содержимое файла для коммита
        commit_message: Сообщение коммита
    
    Returns:
        Dict с ключами:
        - success: bool - успешность операции
        - message: str - сообщение о результате
        - commit_sha: str | None - SHA коммита (если успешно)
    """
    try:
        if not settings.GITLAB_URL or not settings.GITLAB_TOKEN:
            logger.error("GitLab URL или токен не настроены")
            return {
                "success": False,
                "message": "GitLab не настроен. Укажите GITLAB_URL и GITLAB_TOKEN в .env файле",
                "commit_sha": None
            }
        
        gl = gitlab.Gitlab(settings.GITLAB_URL, private_token=settings.GITLAB_TOKEN)
        
        try:
            gl.auth()
        except Exception as e:
            logger.error(f"Ошибка аутентификации в GitLab: {e}")
            return {
                "success": False,
                "message": f"Ошибка аутентификации в GitLab. Проверьте GITLAB_TOKEN и GITLAB_URL. Детали: {str(e)}",
                "commit_sha": None
            }
        
        try:
            project = gl.projects.get(repo_id)
        except gitlab.exceptions.GitlabGetError as e:
            error_msg = str(e)
            logger.error(f"Ошибка получения проекта {repo_id}: {error_msg}")
            
            if "404" in error_msg or "Not Found" in error_msg:
                message = (
                    f"Репозиторий с ID '{repo_id}' не найден. "
                    f"Проверьте:\n"
                    f"1. Правильность ID репозитория (можно использовать путь вида 'namespace/project')\n"
                    f"2. Что у токена есть права доступа к этому репозиторию\n"
                    f"3. Что репозиторий существует и доступен"
                )
            elif "403" in error_msg or "Forbidden" in error_msg:
                message = (
                    f"Нет доступа к репозиторию '{repo_id}'. "
                    f"Проверьте права токена (нужны права 'api' и 'write_repository')"
                )
            else:
                message = f"Не удалось получить доступ к репозиторию '{repo_id}': {error_msg}"
            
            return {
                "success": False,
                "message": message,
                "commit_sha": None
            }
        except gitlab.exceptions.GitlabHttpError as e:
            logger.error(f"HTTP ошибка при получении проекта {repo_id}: {e}")
            return {
                "success": False,
                "message": f"HTTP ошибка при доступе к репозиторию '{repo_id}': {str(e)}",
                "commit_sha": None
            }
        
        try:
            project.branches.get(branch)
        except gitlab.exceptions.GitlabGetError:
            try:
                default_branch = project.default_branch
                project.branches.create({
                    'branch': branch,
                    'ref': default_branch
                })
                logger.info(f"Создана новая ветка {branch}")
            except Exception as e:
                logger.error(f"Ошибка создания ветки {branch}: {e}")
                return {
                    "success": False,
                    "message": f"Не удалось создать ветку {branch}: {str(e)}",
                    "commit_sha": None
                }
        
        try:
            file = project.files.get(file_path=file_path, ref=branch)
            file.content = content
            file.save(branch=branch, commit_message=commit_message)
            commits = project.commits.list(ref_name=branch, per_page=1)
            commit_sha = commits[0].id if commits else None
            
            logger.info(f"Файл {file_path} обновлён в ветке {branch}, коммит: {commit_sha}")
            return {
                "success": True,
                "message": f"Файл {file_path} успешно обновлён в ветке {branch}",
                "commit_sha": commit_sha
            }
        except gitlab.exceptions.GitlabGetError:
            try:
                project.files.create({
                    'file_path': file_path,
                    'branch': branch,
                    'content': content,
                    'commit_message': commit_message
                })
                commits = project.commits.list(ref_name=branch, per_page=1)
                commit_sha = commits[0].id if commits else None
                
                logger.info(f"Файл {file_path} создан в ветке {branch}, коммит: {commit_sha}")
                return {
                    "success": True,
                    "message": f"Файл {file_path} успешно создан в ветке {branch}",
                    "commit_sha": commit_sha
                }
            except Exception as e:
                logger.error(f"Ошибка создания файла {file_path}: {e}")
                return {
                    "success": False,
                    "message": f"Не удалось создать файл {file_path}: {str(e)}",
                    "commit_sha": None
                }
        except Exception as e:
            logger.error(f"Ошибка при работе с файлом {file_path}: {e}")
            return {
                "success": False,
                "message": f"Ошибка при работе с файлом: {str(e)}",
                "commit_sha": None
            }
    
    except gitlab.exceptions.GitlabAuthenticationError:
        logger.error("Ошибка аутентификации в GitLab")
        return {
            "success": False,
            "message": "Ошибка аутентификации. Проверьте GITLAB_TOKEN.",
            "commit_sha": None
        }
    except Exception as e:
        logger.error(f"Неожиданная ошибка при коммите в GitLab: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Неожиданная ошибка: {str(e)}",
            "commit_sha": None
        }


def fetch_defects(
    repo_id: int | str,
    labels: List[str] | None = None,
    state: str = "all",
    max_issues: int = 10
) -> Dict[str, Any]:
    """
    Fetch issues (defects) from GitLab project.

    Returns:
        {
            "success": bool,
            "issues": list[dict(title, description, labels, assignees, state)],
            "count": int,
            "message": str | None
        }
    """
    labels = labels or ["bug"]

    try:
        if not settings.GITLAB_URL or not settings.GITLAB_TOKEN:
            logger.error("GitLab not configured for defects fetch")
            return {
                "success": False,
                "issues": [],
                "count": 0,
                "message": "GitLab не настроен. Укажите GITLAB_URL и GITLAB_TOKEN в .env файле",
            }

        gl = gitlab.Gitlab(settings.GITLAB_URL, private_token=settings.GITLAB_TOKEN)
        gl.auth()
        project = gl.projects.get(repo_id)

        def to_issue_dict(issue, fallback: bool = False) -> dict:
            created_at = issue.created_at
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()
            assignees_attr = getattr(issue, "assignees", None)
            assignees_list = []
            if assignees_attr:
                try:
                    assignees_list = [a.username for a in assignees_attr]
                except TypeError:
                    assignees_list = []
            return {
                "id": getattr(issue, "iid", getattr(issue, "id", None)),
                "title": issue.title,
                "description": issue.description or "",
                "labels": list(issue.labels) if getattr(issue, "labels", None) else [],
                "assignees": assignees_list,
                "state": getattr(issue, "state", None),
                "created_at": created_at,
                "fallback": fallback,
            }

        issues = project.issues.list(
            state=state,
            labels=labels,
            order_by="created_at",
            sort="desc",
            per_page=max_issues or 20,
            get_all=True if max_issues == 0 else False,
        )

        slice_list = issues if max_issues == 0 else issues[:max_issues]
        defects = [to_issue_dict(issue) for issue in slice_list]

        if not defects and labels:
            fallback_issues = project.issues.list(
                state=state,
                order_by="created_at",
                sort="desc",
                per_page=max_issues or 20,
                get_all=True if max_issues == 0 else False,
            )
            slice_fallback = fallback_issues if max_issues == 0 else fallback_issues[:max_issues]
            defects = [to_issue_dict(issue, fallback=True) for issue in slice_fallback]
            if defects:
                logger.info(f"Fetched {len(defects)} defects from repo {repo_id} using fallback without labels")

        logger.info(f"Fetched {len(defects)} defects from repo {repo_id}")
        return {"success": True, "issues": defects, "count": len(defects), "message": None}

    except gitlab.exceptions.GitlabGetError as e:
        error_msg = str(e)
        logger.error(f"GitLabGetError while fetching defects: {error_msg}")
        return {"success": False, "issues": [], "count": 0, "message": error_msg}
    except Exception as e:
        logger.error(f"Error fetching defects: {e}")
        return {"success": False, "issues": [], "count": 0, "message": str(e)}