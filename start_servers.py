"""Start both Flask and WebSocket servers."""
import asyncio
import logging
import threading
from src.app import create_app
from src.websocket_server import start_websocket_server
from src.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_flask():
    """Run Flask application in a separate thread."""
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=config.PORT,
        debug=False,
        use_reloader=False
    )


def run_websocket():
    """Run WebSocket server in asyncio event loop."""
    asyncio.run(start_websocket_server())


if __name__ == '__main__':
    logger.info("Starting Neuro-Caller servers...")
    logger.info(f"Flask server will run on port {config.PORT}")
    logger.info(f"WebSocket server will run on port {config.PORT + 1}")

    # Start Flask in a thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run WebSocket in main thread
    try:
        run_websocket()
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
