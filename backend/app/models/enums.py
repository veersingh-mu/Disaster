import enum


class UserRole(str, enum.Enum):
    ANALYST = "analyst"


class BreachType(str, enum.Enum):
    STRUCTURAL = "structural"
    LANDSLIDE_GLOF = "landslide_glof"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PipelineStage(str, enum.Enum):
    DEM_FETCH = "dem_fetch"
    BREACH_ESTIMATION = "breach_estimation"
    FLOOD_ROUTING = "flood_routing"
    SUMMARY_GENERATION = "summary_generation"


class ExportFormat(str, enum.Enum):
    PDF = "pdf"
    JSON = "json"
