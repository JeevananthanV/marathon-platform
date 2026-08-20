from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Application status")
    project: str = Field(description="Project name")
    version: str = Field(description="Project version")
    database: str = Field(description="Database connectivity status: healthy, degraded, or not_configured")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
