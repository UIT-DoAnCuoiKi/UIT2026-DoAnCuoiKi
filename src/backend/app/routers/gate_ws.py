import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.gate_hub import gate_hub

router = APIRouter()


@router.websocket("/ws/gate")
async def ws_gate(ws: WebSocket) -> None:
    gate_hub.bind_loop(asyncio.get_running_loop())
    await ws.accept()
    queue = await gate_hub.subscribe()
    try:
        while True:
            event = await queue.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        gate_hub.unsubscribe(queue)
