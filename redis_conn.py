from fastapi import FastAPI
from redis import Redis
from contextlib import asynccontextmanager
import httpx
import json

# ─── Use lifespan instead of deprecated on_event ─────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = Redis(host='localhost', port=6379, decode_responses=True)
    app.state.http_client = httpx.AsyncClient()
    yield
    # Shutdown
    app.state.redis.close()
    await app.state.http_client.aclose()

app = FastAPI(lifespan=lifespan)


@app.get('/entries')
async def read_item():
    redis = app.state.redis
    cache_key = "entries"

    # 1. Check cache
    cached = redis.get(cache_key)
    if cached:
        return {"source": "cache", "data": json.loads(cached)}

    # 2. Cache miss — fetch from API
    response = await app.state.http_client.get('https://api.publicapis.org/entries')
    data = response.json()

    # 3. Store in cache (TTL: 5 minutes)
    redis.setex(cache_key, 300, json.dumps(data))

    return {"source": "api", "data": data}


'''
Above is example of request level caching where we have read heavy apis
'''