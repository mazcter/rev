import time
import uuid
from collections import defaultdict, deque
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

EMAIL = "24f1000019@ds.study.iitm.ac.in"
ALLOWED_ORIGIN = "https://app-gz6rby.example.com"
RATE_LIMIT = 14
WINDOW_SECONDS = 10

app = FastAPI()
_buckets: dict[str, deque] = defaultdict(deque)


def _cors_headers(origin: str | None) -> dict:
    headers = {"Vary": "Origin"}
    if origin == ALLOWED_ORIGIN:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "*"
    return headers


@app.middleware("http")
async def combined_middleware(request: Request, call_next):
    origin = request.headers.get("origin")

    if request.method == "OPTIONS":
        resp = JSONResponse(content={}, status_code=200)
        for k, v in _cors_headers(origin).items():
            resp.headers[k] = v
        return resp

    incoming_id = request.headers.get("X-Request-ID")
    request_id = incoming_id if incoming_id else str(uuid.uuid4())
    request.state.request_id = request_id

    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.monotonic()
    bucket = _buckets[client_id]
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        resp = JSONResponse(content={"detail": "Too Many Requests"}, status_code=429)
        resp.headers["X-Request-ID"] = request_id
        for k, v in _cors_headers(origin).items():
            resp.headers[k] = v
        return resp

    bucket.append(now)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    for k, v in _cors_headers(origin).items():
        response.headers[k] = v
    return response


@app.get("/ping")
async def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}
