"""OpenAI Realtime API client for low-latency voice conversations."""
import asyncio
import json
import logging
import base64
import websockets
from typing import Optional, Callable
from src.config import config

logger = logging.getLogger(__name__)


class RealtimeAPIClient:
    """Client for OpenAI Realtime API with WebSocket support."""

    def __init__(self):
        """Initialize Realtime API client."""
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.api_key = config.OPENAI_API_KEY
        self.url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        self.session_id: Optional[str] = None
        self.audio_callback: Optional[Callable] = None

    async def connect(self):
        """Connect to OpenAI Realtime API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.ws = await websockets.connect(
                self.url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=20
            )

            logger.info("Connected to OpenAI Realtime API")

            # Configure session
            await self.configure_session()

            return True

        except Exception as e:
            logger.error(f"Error connecting to OpenAI Realtime API: {e}")
            return False

    async def configure_session(self):
        """Configure the Realtime API session with instructions."""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": f"""Вы - Анна, дружелюбный рекрутер такси-сервиса {config.TAXI_BRAND_NAME}.

Ваша задача - убедить человека стать водителем в нашем сервисе.

Важные правила:
1. Говорите кратко и естественно, как в живом разговоре
2. Представьтесь в начале разговора
3. Узнайте имя собеседника
4. Расскажите о преимуществах работы водителем:
   - Гибкий график - работайте когда удобно
   - Еженедельные выплаты без задержек
   - Бонусы до 50,000 рублей для новых водителей
   - Поддержка 24/7 по любым вопросам
   - Страховка и защита водителя
5. Ответьте на вопросы собеседника честно и подробно
6. Если человек заинтересован, предложите оставить контакты для менеджера
7. Если человек отказывается, вежливо попрощайтесь
8. Говорите только на русском языке
9. Будьте дружелюбны, энергичны и профессиональны
10. Не перебивайте собеседника, дожидайтесь паузы""",
                "voice": "alloy",  # Options: alloy, echo, shimmer
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "temperature": 0.8,
                "max_response_output_tokens": 4096
            }
        }

        await self.ws.send(json.dumps(session_config))
        logger.info("Session configured with recruitment instructions")

    async def send_audio(self, audio_data: str):
        """
        Send audio data to OpenAI.

        Args:
            audio_data: Base64 encoded audio (mulaw or pcm16)
        """
        if not self.ws:
            logger.error("WebSocket not connected")
            return

        try:
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_data
            }
            await self.ws.send(json.dumps(message))

        except Exception as e:
            logger.error(f"Error sending audio: {e}")

    async def commit_audio(self):
        """Commit audio buffer and trigger response."""
        if not self.ws:
            return

        try:
            message = {"type": "input_audio_buffer.commit"}
            await self.ws.send(json.dumps(message))

            # Create response
            response_message = {"type": "response.create"}
            await self.ws.send(json.dumps(response_message))

        except Exception as e:
            logger.error(f"Error committing audio: {e}")

    async def receive_messages(self):
        """Receive and process messages from OpenAI."""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                await self.handle_message(message)

        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")

    async def handle_message(self, message: str):
        """
        Handle incoming message from OpenAI.

        Args:
            message: JSON message from OpenAI
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "session.created":
                self.session_id = data.get("session", {}).get("id")
                logger.info(f"Session created: {self.session_id}")

            elif msg_type == "session.updated":
                logger.info("Session updated successfully")

            elif msg_type == "response.audio.delta":
                # Audio chunk from OpenAI
                audio_data = data.get("delta")
                if audio_data and self.audio_callback:
                    await self.audio_callback(audio_data)

            elif msg_type == "response.audio.done":
                logger.info("Audio response completed")

            elif msg_type == "conversation.item.input_audio_transcription.completed":
                transcript = data.get("transcript", "")
                logger.info(f"User said: {transcript}")

            elif msg_type == "response.text.delta":
                text = data.get("delta", "")
                logger.debug(f"AI text delta: {text}")

            elif msg_type == "response.done":
                logger.info("Response completed")

            elif msg_type == "error":
                error = data.get("error", {})
                logger.error(f"OpenAI error: {error}")

            else:
                logger.debug(f"Received message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def set_audio_callback(self, callback: Callable):
        """
        Set callback for audio output.

        Args:
            callback: Async function to call with audio data
        """
        self.audio_callback = callback

    async def close(self):
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            logger.info("Closed OpenAI Realtime API connection")
