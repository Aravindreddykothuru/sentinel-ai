from .machines import router as machines_router
from .alerts import router as alerts_router
from .copilot import router as copilot_router
from .maintenance import router as maintenance_router
from .production import router as production_router
from .onboarding import router as onboarding_router
from .discovery import router as discovery_router
from .ginning_validation import router as ginning_validation_router
from .twin import router as twin_router

__all__ = [
    "machines_router",
    "alerts_router",
    "copilot_router",
    "maintenance_router",
    "production_router",
    "onboarding_router",
    "discovery_router",
    "ginning_validation_router",
    "twin_router"
]
