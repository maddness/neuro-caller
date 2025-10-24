"""WebSocket server for Twilio Media Streams."""
import asyncio
import logging
import websockets
from src.services.media_stream_handler import handle_media_stream
from src.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def start_websocket_server():
    """Start WebSocket server for Media Streams."""
    port = config.PORT + 1  # WebSocket on PORT + 1 (e.g., 3001)

    logger.info(f"Starting WebSocket server on port {port}")

    server = await websockets.serve(
        handle_media_stream,
        "0.0.0.0",
        port,
        ping_interval=20,
        ping_timeout=20
    )

    logger.info(f"WebSocket server listening on ws://0.0.0.0:{port}")

    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(start_websocket_server())
