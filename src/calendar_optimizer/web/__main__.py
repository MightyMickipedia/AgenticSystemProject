"""Run the web server: python -m calendar_optimizer.web"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "calendar_optimizer.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
