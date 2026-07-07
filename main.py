import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# ─────────────────────────────────────────────────────────────
# FILL THESE IN BEFORE YOU SUBMIT
# ─────────────────────────────────────────────────────────────
MY_EMAIL = "24f2005644@ds.study.iitm.ac.in"          # <-- your logged-in email
EXAM_PAGE_ORIGIN = "https://exam.sanand.workers.dev"  # <-- see README

ASSIGNED_ORIGIN = "https://app-iyyyty.example.com"
RATE_LIMIT = 13        # requests
WINDOW_SECONDS = 10    # seconds


# ─────────────────────────────────────────────────────────────
# Middleware 1: Request context (adds/reuses X-Request-ID)
# ─────────────────────────────────────────────────────────────
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ─────────────────────────────────────────────────────────────
# Middleware 2: Per-client rate limiter (fixed window per X-Client-Id)
# ─────────────────────────────────────────────────────────────
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.buckets: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Preflight requests are handled by CORSMiddleware and should
        # never be counted against a client's quota.
        if request.method == "OPTIONS":
            return await call_next(request)

        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.monotonic()
        bucket = self.buckets[client_id]

        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:
            return JSONResponse(
                {"detail": "Rate limit exceeded, try again later."},
                status_code=429,
            )

        bucket.append(now)
        return await call_next(request)


# ─────────────────────────────────────────────────────────────
# App + Middleware 3: CORS (added LAST so it runs OUTERMOST)
# ─────────────────────────────────────────────────────────────
app = FastAPI()

app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ASSIGNED_ORIGIN, EXAM_PAGE_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],
)


@app.get("/ping")
async def ping(request: Request):
    return {"email": MY_EMAIL, "request_id": request.state.request_id}
