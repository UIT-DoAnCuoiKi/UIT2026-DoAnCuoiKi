import asyncio
import logging

logger = logging.getLogger("uvicorn.error")


class GateHub:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queues: set[asyncio.Queue] = set()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    def publish(self, event: dict) -> None:
        if self._loop is None:
            # Không nên xảy ra nữa (main.py bind loop lúc khởi động), nhưng nếu
            # có thì phải kêu: rớt im lặng ở đây nghĩa là capture mất khỏi feed
            # realtime mà không ai biết.
            logger.warning("GateHub chưa bind event loop, bỏ qua sự kiện %s", event.get("capture_id"))
            return
        for queue in list(self._queues):
            self._loop.call_soon_threadsafe(queue.put_nowait, event)


gate_hub = GateHub()
