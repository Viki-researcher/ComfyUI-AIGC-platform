from fastapi import APIRouter

from .auth import router as auth_router
from .chat import router as chat_router
from .dashboard import router as dashboard_router
from .dataset import router as dataset_router
from .logs import router as logs_router
from .projects import router as projects_router
from .prompt import router as prompt_router
from .roles import router as roles_router
from .server import router as server_router
from .system import router as system_router
from .stats import router as stats_router
from .users import router as users_router
from .workflow import router as workflow_router

compat_router = APIRouter()

compat_router.include_router(auth_router)
compat_router.include_router(users_router)
compat_router.include_router(roles_router)
compat_router.include_router(system_router)
compat_router.include_router(projects_router)
compat_router.include_router(logs_router)
compat_router.include_router(stats_router)
compat_router.include_router(server_router)
compat_router.include_router(dashboard_router)
compat_router.include_router(dataset_router)
compat_router.include_router(prompt_router)
compat_router.include_router(chat_router)
compat_router.include_router(workflow_router)

__all__ = ["compat_router"]
