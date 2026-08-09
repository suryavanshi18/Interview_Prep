"""
main.py — Sliding-window rate limiter behind FastAPI.

Run:
    pip install fastapi uvicorn
    uvicorn main:app --reload
"""

import time
import asyncio
import threading
import collections
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, HTTPException


# ---------------- Rate limiter ----------------
class Ratelimiter:
    def __init__(self, maxcap, maxtime):
        self.maxcap = maxcap
        self.maxtime = maxtime
        self.map = collections.defaultdict(collections.deque)
        # One lock protects the whole map. Fine for this scale.
        self.lock = threading.Lock()

    def isNewReqAllowed(self, clientId, timestamp):
        with self.lock:
            dq = self.map[clientId]
            while dq and dq[0] < timestamp - self.maxtime:
                dq.popleft()
            if len(dq) < self.maxcap:
                dq.append(timestamp)
                return True
            return False

    def stats(self, clientId, timestamp):
        """Read-only view for GET /stats. Doesn't mutate the deque."""
        with self.lock:
            dq = self.map.get(clientId)
            if not dq:
                return {"used": 0, "remaining": self.maxcap}
            active = sum(1 for t in dq if t >= timestamp - self.maxtime)
            return {"used": active, "remaining": max(0, self.maxcap - active)}

    def cleanup(self, timestamp):
        """Drop clients whose *newest* timestamp is outside the window."""
        with self.lock:
            stale = [
                cid for cid, dq in self.map.items()
                if not dq or dq[-1] < timestamp - self.maxtime
            ]
            for cid in stale:
                del self.map[cid]
            return len(stale)


# ---------------- Config ----------------
MAX_CAP = 5     # requests
WINDOW  = 60    # seconds
CLEANUP_INTERVAL = 30  # seconds

limiter = Ratelimiter(MAX_CAP, WINDOW)


# ---------------- Background cleanup ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs a periodic cleanup task while the app is alive."""
    stop = asyncio.Event()

    async def periodic_cleanup():
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=CLEANUP_INTERVAL)
            except asyncio.TimeoutError:
                limiter.cleanup(time.time())

    task = asyncio.create_task(periodic_cleanup())
    yield
    stop.set()
    await task


app = FastAPI(title="Rate Limiter", lifespan=lifespan)


# ---------------- Endpoints ----------------
# Endpoints are `def` (sync), not `async def`, because the limiter uses a
# threading.Lock. FastAPI runs sync endpoints in a threadpool, so multiple
# requests still process concurrently.

@app.post("/check/{client_id}")
def check(client_id: str):
    """Ask the limiter whether this client can make a request right now."""
    now = time.time()
    allowed = limiter.isNewReqAllowed(client_id, now)
    if not allowed:
        # 429 is the HTTP status for rate limiting.
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {MAX_CAP} per {WINDOW}s",
            headers={"Retry-After": str(WINDOW)},
        )
    return {"allowed": True, "client_id": client_id, "timestamp": now}


@app.get("/stats/{client_id}")
def stats(client_id: str):
    return limiter.stats(client_id, time.time())


@app.post("/cleanup")
def cleanup():
    removed = limiter.cleanup(time.time())
    return {"clients_removed": removed}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "clients_tracked": len(limiter.map),
        "cap": MAX_CAP,
        "window_seconds": WINDOW,
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)