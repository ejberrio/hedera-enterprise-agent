"""Hedera Enterprise Agent — FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from agent.core import build_agent
from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        build_agent()
    except Exception as e:
        logging.warning("Agent startup failed (missing/invalid credentials?): %s", e)
    yield


app = FastAPI(
    title="Hedera Enterprise Agent",
    description="Enterprise-grade AI agent with Hedera blockchain tools and plugin extensibility",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)


@app.get("/")
async def root():
    return FileResponse("static/index.html")
