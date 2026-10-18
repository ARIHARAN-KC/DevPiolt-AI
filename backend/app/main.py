from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.tasks import router as tasks_router

app = FastAPI(
    title = "DevPilot AI",
    description= "An evidence-backed autonomus coding agent.",
    version = "0.1.0"
)

app.include_router(health_router)
app.include_router(tasks_router)