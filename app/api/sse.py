import json
import asyncio
from django.conf import settings
from django.http import StreamingHttpResponse
from ninja.router import Router
from redis import asyncio as aioredis
from django_redis import get_redis_connection

from app.api.auth.user import ServiceUserJWTAuth

sse_router = Router()

def emit_event(user_id: str, event_name: str, data: dict):
    conn = get_redis_connection("default")
    channel = f"user_{user_id}_events"
    payload = {
        "event": event_name,
        "data": data
    }
    conn.publish(channel, json.dumps(payload))


async def redis_event_stream(user_id: str):
    redis = aioredis.from_url(settings.CACHES["default"]["LOCATION"])
    pubsub = redis.pubsub()

    channel_name = f"user_{user_id}_events"
    await pubsub.subscribe(channel_name)

    yield ": ok\n\n"

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=20.0
                )

                if message:
                    data = message["data"].decode("utf-8")
                    yield f"data: {data}\n\n"

            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        await pubsub.unsubscribe(channel_name)
    finally:
        await pubsub.aclose()
        await redis.aclose()


@sse_router.get("/events", auth=ServiceUserJWTAuth())
async def sse_endpoint(request):
    response = StreamingHttpResponse(
        redis_event_stream(request.user.id),
        content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
