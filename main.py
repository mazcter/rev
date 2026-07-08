import time
import uuid
from collections import defaultdict, deque
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

EMAIL = "24f1000019@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = {
    "https://app-gz6rby.example.com",
    "https://exam.sanand.workers.dev",   # exam page origin used for grading — replace with actual exam origin shown to you
}

RATE_LIMIT = 14          # requests
WINDOW_SECONDS = 10      # per this window

app = FastAPI()

# client_id -> deque of request timestamps
_buckets: dict[str, deque] = defaultdict(deque)


def _is_allowed_origin(origin: str | None) -> bool:
    return origin in ALLOWED_ORIGINS


def _cors_headers(origin: str | None) -> dict:
    headers = {"Vary": "Origin"}
    if _is_allowed_origin(origin):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "*"
    return headers


@app.middleware("http")
async def combined_middleware(request: Request, call_next):
    start = time.perf_counter()
    origin = request.headers.get("origin")

    # --- Preflight handling ---
    if request.method == "OPTIONS":
        resp = JSONResponse(content={}, status_code=200)
        for k, v in _cors_headers(origin).items():
            resp.headers[k] = v
        return resp

    # --- Request context: request_id ---
    incoming_id = request.headers.get("X-Request-ID")
    request_id = incoming_id if incoming_id else str(uuid.uuid4())
    request.state.request_id = request_id

    # --- Rate limiting (per X-Client-Id) ---
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.monotonic()
    bucket = _buckets[client_id]

    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        resp = JSONResponse(
            content={"detail": "Too Many Requests"},
            status_code=429,
        )
        resp.headers["X-Request-ID"] = request_id
        for k, v in _cors_headers(origin).items():
            resp.headers[k] = v
        return resp

    bucket.append(now)

    # --- Proceed to endpoint ---
    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"
    for k, v in _cors_headers(origin).items():
        response.headers[k] = v

    return response


@app.get("/ping")
async def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}
