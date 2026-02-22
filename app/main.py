"""FastAPI + lifespan (DB + Agent 초기화)"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.agent import AgentWorker
from app.config import load_config
from app.dashboard import build_dashboard_html
from app.database import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    db = Database(config.db_path)
    await db.init()
    agent = AgentWorker(config, db)
    app.state.db = db
    app.state.agent = agent
    target_msg = config.target_project or "(none — use Plans for multi-target)"
    logging.getLogger(__name__).info("Claude Pilot started — target: %s", target_msg)
    yield
    await agent.stop_loop()
    await db.close()


app = FastAPI(title="Claude Pilot", lifespan=lifespan)


# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return build_dashboard_html()


# Health
@app.get("/health")
async def health():
    return {"status": "ok"}


# API routes
from app.api.routes import router  # noqa: E402
from app.reports import report_router  # noqa: E402

app.include_router(router)
app.include_router(report_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=9000)
