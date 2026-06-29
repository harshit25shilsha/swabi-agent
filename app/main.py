from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers.chat    import router  as chat_router
from app.routers.activity import router as activity_router
from app.routers.package  import router as package_router
from app.routers.agent    import router as agent_router
from app.routers.auth     import router as auth_router
from fastapi.middleware.cors import CORSMiddleware


from app.graph.agent  import build_graph
from app.config       import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    try:
        import importlib

        module = importlib.import_module("langgraph.checkpoint.aiosqlite")
        AsyncSqliteSaver = module.AsyncSqliteSaver
        checkpointer = AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB_PATH)
        logger.info("Using SQLite checkpointer: %s", settings.CHECKPOINT_DB_PATH)
    except Exception:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
        logger.warning("SQLite checkpointer unavailable — using in-memory (sessions won't survive restart)")

    app.state.graph = build_graph(checkpointer)
    logger.info("Agent graph compiled and ready")
    yield


app = FastAPI(
    title="Swabi AI Agent",
    version="0.4.0",
    description="AI-powered travel assistant for Swabi — search, recommend, and book trips.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(activity_router)
app.include_router(package_router)
app.include_router(agent_router)


@app.get("/", tags=["Health"])
async def health():
    return {"service": "swabi-agent", "status": "running", "version": "0.4.0"}