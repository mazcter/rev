import time
import uuid
from collections import defaultdict, deque
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

EMAIL = "24f1000019@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = {
    "https://app-gz6rby.example.com",
    "https://exam.sanand.workers.dev",
}

RATE_LIMIT = 14
WINDOW_SECONDS = 10

app = FastAPI()
_buckets = defaultdict(deque)


@app.middleware("http")
async def combined_middleware(request: Request, call_next):
    origin = request.headers.get("origin")

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    if request.method == "OPTIONS":
        resp = JSONResponse(content={}, status_code=200)
        resp.headers["X-Request-ID"] = request_id
        if origin in ALLOWED_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp

    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.monotonic()
    bucket = _buckets[client_id]
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        resp = JSONResponse(content={"detail": "Too Many Requests"}, status_code=429)
        resp.headers["X-Request-ID"] = request_id
        resp.headers["Retry-After"] = "1"
        if origin in ALLOWED_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin
        return resp

    bucket.append(now)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    return response


@app.get("/ping")
async def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}
