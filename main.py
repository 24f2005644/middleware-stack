from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import uuid
import time

app = FastAPI()

EMAIL = "24f2005644@ds.study.iitm.ac.in"

# --------------------------------------------------
# RATE LIMIT SETTINGS
# --------------------------------------------------

RATE_LIMIT = 13
WINDOW = 10

client_requests = {}

# --------------------------------------------------
# REQUEST CONTEXT MIDDLEWARE
# --------------------------------------------------

@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# --------------------------------------------------
# RATE LIMIT MIDDLEWARE
# --------------------------------------------------

@app.middleware("http")
async def rate_limit(request: Request, call_next):

    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    if client_id not in client_requests:
        client_requests[client_id] = []

    timestamps = client_requests[client_id]

    # keep only requests within last 10 seconds
    timestamps[:] = [
        ts for ts in timestamps
        if now - ts < WINDOW
    ]

    if len(timestamps) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded"
            },
            headers={
                "Retry-After": "10"
            }
        )

    timestamps.append(now)

    return await call_next(request)


# --------------------------------------------------
# CORS
# --------------------------------------------------

allowed_origins = [
    "https://app-iyyyty.example.com",

    # IMPORTANT:
    # add exam origin if provided in portal
    # example:
    # "https://exam.sanand.workers.dev"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# ENDPOINT
# --------------------------------------------------

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }
