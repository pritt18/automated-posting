import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import PostingRequest, PostingResponse, HealthResponse
from app.services.posting_service import posting_service
from app.config import settings

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("automated_posting.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting Automated Posting Service on %s:%d (Simulation Mode: %s)",
        settings.app_host,
        settings.app_port,
        settings.simulation_mode
    )
    yield
    logger.info("Automated Posting Service shutting down.")


app = FastAPI(
    title="Automated Multi-Platform Posting Service",
    description="Cross-platform API service to publish broadcast announcements and CTA messages across multiple communication platforms.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for frontend dashboard or cross-origin client usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """
    Format validation errors into concise, human-readable messages.
    """
    errors = []
    for err in exc.errors():
        location = " -> ".join(str(loc) for loc in err.get("loc", []))
        message = err.get("msg", "Validation error")
        errors.append(f"{location}: {message}")

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Input validation failed.",
            "errors": errors
        }
    )


@app.get("/", tags=["General"])
async def root():
    return {
        "service": "Automated Multi-Platform Posting Service",
        "status": "operational",
        "docs": "/docs",
        "endpoint": "/posting"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        platforms_loaded=len(posting_service.platforms)
    )


@app.post(
    "/posting",
    response_model=PostingResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish broadcast message across configured platforms",
    description="Validates the message (<=200 chars, exactly one valid CTA link) and broadcasts to all integrated platforms.",
    tags=["Posting"]
)
async def post_message(payload: PostingRequest):
    cta_url = payload.get_cta_url()
    logger.info("Received posting request (CTA: %s, Length: %d chars)", cta_url, len(payload.message))

    response = await posting_service.broadcast(
        message=payload.message,
        cta_url=cta_url
    )

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True
    )
