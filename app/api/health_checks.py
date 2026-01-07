from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import connections


async def check_database():
    try:

        @sync_to_async
        def run_query():
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")

        await run_query()
        return "healthy"
    except Exception as e:
        return f"unhealthy: {e}"


async def check_cache():
    try:

        @sync_to_async
        def cache_ops():
            cache.set("health_check", "ok", 1)
            return cache.get("health_check") == "ok"

        healthy = await cache_ops()
        return "healthy" if healthy else "unhealthy"
    except Exception as e:
        return f"unhealthy: {e}"


HEALTH_CHECKS = {
    "database": check_database,
    "cache": check_cache,
}
