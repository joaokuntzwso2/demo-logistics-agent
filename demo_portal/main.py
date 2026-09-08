from __future__ import annotations

import uvicorn

from .app import app
from .config import load_settings

if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.portal_port)
