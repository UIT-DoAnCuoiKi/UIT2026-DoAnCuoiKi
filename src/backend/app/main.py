from fastapi import FastAPI

from app.routers import auth, captures, config, gate_ws, health, images, readings, sessions, stats, users


def create_app() -> FastAPI:
    app = FastAPI(title="Parking backend")
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(captures.router)
    app.include_router(sessions.router)
    app.include_router(readings.router)
    app.include_router(images.router)
    app.include_router(stats.router)
    app.include_router(config.router)
    app.include_router(gate_ws.router)
    return app


app = create_app()
