import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

EMAIL = "24f1000019@ds.study.iitm.ac.in"
ALLOWED_ORIGIN = "https://YOUR-ASSIGNED-ORIGIN.example.com"  # replace with your assigned origin

app = FastAPI()


@app.middleware("http")
async def combined_middleware(request: Request, call_next):
    start = time.perf_counter()

    incoming_id = request.headers.get("X-Request-ID")
    request_id = incoming_id if incoming_id else str(uuid.uuid4())
    request.state.request_id = request_id

    origin = request.headers.get("origin")

    if request.method == "OPTIONS":
        if origin == ALLOWED_ORIGIN:
            resp = JSONResponse(content={}, status_code=200)
            resp.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "*"
            resp.headers["Vary"] = "Origin"
        else:
            resp = JSONResponse(content={}, status_code=400)
        resp.headers["X-Request-ID"] = request_id
        resp.headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"
        return resp

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"

    if origin == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Vary"] = "Origin"

    return response


@app.get("/stats")
async def stats(values: str):
    nums = [int(v.strip()) for v in values.split(",") if v.strip() != ""]

    if not nums:
        return JSONResponse(
            content={"email": EMAIL, "count": 0, "sum": 0, "min": None, "max": None, "mean": 0},
            status_code=200,
        )

    count = len(nums)
    total = sum(nums)
    mn = min(nums)
    mx = max(nums)
    mean = total / count

    return {
        "email": EMAIL,
        "count": count,
        "sum": total,
        "min": mn,
        "max": mx,
        "mean": mean,
    }
