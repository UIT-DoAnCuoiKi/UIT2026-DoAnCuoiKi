from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.config import settings
from app.routers import auth, captures, config, devices, gate_ws, health, images, incidents, payments, readings, registry, sessions, shifts, spaces, stats, sync, users


def _operation_id(route: APIRoute) -> str:
    # operationId = tên hàm handler (đã đảm bảo duy nhất toàn app). Orval dùng
    # nó đặt tên hook, cho ra useLogin/useConfirmEntry thay vì tên mặc định dài.
    return route.name


def create_app() -> FastAPI:
    app = FastAPI(
        title="Parking backend",
        version="0.1.0",
        generate_unique_id_function=_operation_id,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(captures.router)
    app.include_router(sessions.router)
    app.include_router(readings.router)
    app.include_router(images.router)
    app.include_router(stats.router)
    app.include_router(config.router)
    app.include_router(spaces.router)
    app.include_router(shifts.router)
    app.include_router(payments.router)
    app.include_router(devices.router)
    app.include_router(incidents.router)
    app.include_router(registry.router)
    app.include_router(sync.router)
    app.include_router(gate_ws.router)
    return app


app = create_app()
