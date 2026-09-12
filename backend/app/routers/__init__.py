from backend.app.routers.ai import router as ai_router
from backend.app.routers.alerts import router as alerts_router
from backend.app.routers.case_studies import router as case_studies_router
from backend.app.routers.dem import router as dem_router
from backend.app.routers.exports import router as exports_router
from backend.app.routers.scenarios import router as scenarios_router

__all__ = [
    "scenarios_router",
    "case_studies_router",
    "dem_router",
    "exports_router",
    "alerts_router",
    "ai_router",
]
