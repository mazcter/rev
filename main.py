import time
import uuid
from collections import defaultdict, deque
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

EMAIL = "24f1000019@ds.study.iitm.ac.in"

EXAM_PAGE_ORIGINS = {
    "https://app-gz6rby.example.com",
    "https://exam.sanand.workers.dev",
}

BUCKET_SIZE = 14
WINDOW_SECONDS = 10

app = FastAPI()

request_buckets = defaultdict(deque)


@app.middleware("http")
async def combined_middleware(request: Request, call_next):
    incoming_id = request.headers.get("X-Request-ID")
    request_id = incoming_id if incoming_id else str(uuid.uuid4())
    request.state.request_id = request_id

    origin = request.headers.get("origin")

    if request.method == "OPTIONS":
        if origin in EXAM_PAGE_ORIGINS:
            resp = JSONResponse(content={}, status_code=200)
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "*"
            resp.headers["Vary"] = "Origin"
        else:
            resp = JSONResponse(content={}, status_code=400)
        resp.headers["X-Request-ID"] = request_id
        return resp

    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()
    dq = request_buckets[client_id]

    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()

    if len(dq) >= BUCKET_SIZE:
        retry_after = max(1, int(WINDOW_SECONDS - (now - dq[0])))
        resp = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        resp.headers["Retry-After"] = str(retry_after)
        resp.headers["X-Request-ID"] = request_id
        if origin in EXAM_PAGE_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
        return resp

    dq.append(now)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if origin in EXAM_PAGE_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response


@app.get("/ping")
async def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}
