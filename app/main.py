from fastapi import FastAPI

from app.routers.chat import router
from app.routers.activity import router as activity_router
from app.routers.package import router as package_router
from app.routers.agent import router as agent_router



app = FastAPI(
    title="Swabi Agent"
)

app.include_router(router)
app.include_router(activity_router)
app.include_router(package_router)
app.include_router(agent_router)


@app.get(
    "/",
    summary="Check service status",
    description="Use this endpoint to confirm the Swabi Agent API is running."
)
def root():

    return {
        "service": "swabi-agent",
        "status": "running"
    }
