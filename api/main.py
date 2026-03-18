from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import recommend, health
from api.middleware.logging import LoggingMiddleware
from chic_finder.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Logging Middleware
app.add_middleware(LoggingMiddleware)

# Route registration
app.include_router(recommend.router, prefix=settings.API_V1_STR, tags=["recommendation"])
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])

@app.get("/")
async def root():
    return {"message": "Welcome to ChicFinder API"}
