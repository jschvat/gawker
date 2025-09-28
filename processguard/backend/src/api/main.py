from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
from pathlib import Path

from .routes import router, set_daemon
from ..core.daemon import ProcessGuardDaemon
from ..utils.logging import setup_logging, get_logger

def create_app(config_file: str = "/etc/processguard/config.json") -> FastAPI:
    app = FastAPI(
        title="ProcessGuard API",
        description="REST API for ProcessGuard monitoring system",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    daemon = ProcessGuardDaemon(config_file)
    set_daemon(daemon)

    app.include_router(router, prefix="/api/v1")

    frontend_path = Path(__file__).parent.parent.parent.parent / "frontend" / "build"
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(daemon.start())

    @app.on_event("shutdown")
    async def shutdown_event():
        daemon.stop()

    return app

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ProcessGuard API Server")
    parser.add_argument("-c", "--config", default="/etc/processguard/config.json",
                       help="Configuration file path")
    parser.add_argument("-h", "--host", default="0.0.0.0",
                       help="Host to bind to")
    parser.add_argument("-p", "--port", type=int, default=7500,
                       help="Port to bind to")
    parser.add_argument("--reload", action="store_true",
                       help="Enable auto-reload for development")

    args = parser.parse_args()

    setup_logging()
    logger = get_logger(__name__)

    logger.info(f"Starting ProcessGuard API server on {args.host}:{args.port}")

    app = create_app(args.config)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()