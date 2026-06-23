from contextlib import asynccontextmanager
import aiosqlite
from fastapi import FastAPI

from app.routers.chat import router
from app.routers.activity import router as activity_router
from app.routers.package import router as package_router
from app.routers.agent import router as agent_router
from app.graph.agent import build_graph
from app.config import settings

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    
    logger.info("Swabi AI agent starting up")
    logger.info("Checkpoint DB: %s", settings.CHECKPOINT_DB_PATH)
    
    
    conn = await aiosqlite.connect(settings.CHECKPOINT_DB_PATH)
    checkpointer = AsyncSqliteSaver(conn)
    
    
    # Creates the checkpoint tables on first run if they don't already
    # exist; harmless no-op on subsequent startups against the same DB File.
    await checkpointer.setup()
    
    app.state.graph = build_graph(checkpointer)
    logger.info("Agent graph compiled and ready")
    
    
    yield
    logger.info("Swabi AI Agent shutting down")
    await conn.close()
    


app = FastAPI(
    title="Swabi Agent",
    lifespan= lifespan
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
