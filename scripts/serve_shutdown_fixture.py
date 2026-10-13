"""Isolated shutdown regression: a real ASGI request that never completes."""

import asyncio
import os
import sys
from pathlib import Path

backend = Path(os.environ.get("TROGLODAW_TEST_APP", "backend/app.py")).resolve().parent
sys.path.insert(0, str(backend))
import app  # noqa: E402

if os.environ.get("SYNTHETIC_FRONTEND"):
    app.FRONTEND = Path(os.environ["SYNTHETIC_FRONTEND"])
original_create = app.create_app


def create(*args, **kwargs):
    api = original_create(*args, **kwargs)

    @api.get("/api/fixture/blocked")
    async def blocked():
        Path(os.environ["TROGLODAW_TEST_BLOCKED_MARKER"]).write_text("entered")
        await asyncio.Event().wait()

    api.router.routes.sort(key=lambda route: getattr(route, "name", None) == "frontend")
    return api


setattr(app, "create_app", create)
if os.environ.get("TROGLODAW_TEST_UNBOUNDED_SHUTDOWN") == "1":
    # Reproduce a previously shipped updater's permanently pending HTTP teardown.
    original_config = app.uvicorn.Config

    class UnboundedConfig(original_config):
        def __init__(self, *args, **kwargs):
            kwargs["timeout_graceful_shutdown"] = None
            super().__init__(*args, **kwargs)

    setattr(app.uvicorn, "Config", UnboundedConfig)

app.main()
