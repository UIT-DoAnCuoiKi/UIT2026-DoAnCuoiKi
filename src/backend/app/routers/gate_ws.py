import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import db_session_factory
from app.deps import _user_from_token
from app.services.gate_hub import gate_hub

router = APIRouter()


@router.websocket("/ws/gate")
async def ws_gate(
    ws: WebSocket,
    token: str | None = Query(None),
    session_factory: type[Session] = Depends(db_session_factory),
) -> None:
    # Feed phát biển số và ảnh của mọi làn, nên phải xác thực trước accept().
    # Đóng session ngay sau khi kiểm tra token: Depends(get_db) sẽ giữ connection suốt vòng lặp bên dưới.
    db = session_factory()
    try:
        if token is None:
            raise HTTPException(401)
        _user_from_token(token, db)
    except HTTPException:
        await ws.close(code=1008)
        return
    finally:
        db.close()

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
