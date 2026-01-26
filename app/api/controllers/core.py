import time
import asyncio
from ninja_extra import api_controller, http_get, ControllerBase

from app.api.health_checks import HEALTH_CHECKS
from app.api.schemas.core import MessageSchema, HealthSchema


@api_controller("", tags=["public"])
class CoreController(ControllerBase):
    @http_get(
        "/version",
        operation_id="getAPIVersion",
    )
    def version(self):
        return {
            "version": "1.0.0",
            "framework": "Django Ninja Extra",
            "python": "3.10+",
            "api_docs": "/api/docs",
        }

    @http_get(
        "/health",
        response=MessageSchema,
        operation_id="getAPIHealth",
    )
    def health_check(self):
        return {"message": "Service is healthy"}

    @http_get(
        "/health/detailed",
        response=HealthSchema,
        operation_id="getAPIDetailedHealth",
    )
    async def detailed_health_check(self):
        results = await asyncio.gather(*(func() for func in HEALTH_CHECKS.values()))
        health_mixins = dict(zip(HEALTH_CHECKS.keys(), results))
        overall_status = (
            "healthy"
            if all("healthy" in v for v in health_mixins.values())
            else "degraded"
        )
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "mixins": health_mixins,
        }
