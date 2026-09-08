from __future__ import annotations

import uvicorn

from logistics_common.runtime import chat_agent_port
from .app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=chat_agent_port())
