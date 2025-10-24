"""Twilio Media Stream handler with OpenAI Realtime API integration."""
import asyncio
import json
import logging
import base64
from typing import Optional
import websockets
from src.services.realtime_client import RealtimeAPIClient

logger = logging.getLogger(__name__)


class MediaStreamHandler:
    """Handler for Twilio Media Streams with OpenAI Realtime API."""

    def __init__(self, websocket: websockets.WebSocketServerProtocol):
        """
        Initialize media stream handler.

        Args:
            websocket: Twilio Media Stream WebSocket connection
        """
        self.twilio_ws = websocket
        self.openai_client = RealtimeAPIClient()
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.is_active = True
        self.mark_queue = []
        self.last_assistant_item = None

    async def handle(self):
        """Main handler for media stream."""
        try:
            # Connect to OpenAI
            connected = await self.openai_client.connect()
            if not connected:
                logger.error("Failed to connect to OpenAI")
                return

            # Set audio callback
            self.openai_client.set_audio_callback(self.send_audio_to_twilio)

            # Start receiving from OpenAI
            openai_task = asyncio.create_task(self.openai_client.receive_messages())

            # Process Twilio messages
            await self.process_twilio_messages()

            # Wait for OpenAI task to complete
            await openai_task

        except Exception as e:
            logger.error(f"Error in media stream handler: {e}")
        finally:
            await self.cleanup()

    async def process_twilio_messages(self):
        """Process incoming messages from Twilio."""
        try:
            async for message in self.twilio_ws:
                if not self.is_active:
                    break

                data = json.loads(message)
                event_type = data.get("event")

                if event_type == "connected":
                    logger.info("Twilio Media Stream connected")

                elif event_type == "start":
                    self.stream_sid = data.get("streamSid")
                    self.call_sid = data.get("start", {}).get("callSid")
                    logger.info(f"Stream started - StreamSID: {self.stream_sid}, CallSID: {self.call_sid}")

                    # Send initial greeting prompt to OpenAI
                    await self.send_initial_greeting()

                elif event_type == "media":
                    # Audio data from Twilio (mulaw, base64 encoded)
                    payload = data.get("media", {}).get("payload")
                    if payload:
                        await self.handle_twilio_audio(payload)

                elif event_type == "mark":
                    mark_name = data.get("mark", {}).get("name")
                    logger.debug(f"Mark received: {mark_name}")

                elif event_type == "stop":
                    logger.info("Stream stopped by Twilio")
                    self.is_active = False
                    break

        except websockets.exceptions.ConnectionClosed:
            logger.info("Twilio WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error processing Twilio messages: {e}")

    async def send_initial_greeting(self):
        """Send initial greeting to start the conversation."""
        try:
            # Send a conversation item to trigger OpenAI to speak first
            greeting_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Привет"
                        }
                    ]
                }
            }
            await self.openai_client.ws.send(json.dumps(greeting_message))

            # Trigger response
            response_create = {"type": "response.create"}
            await self.openai_client.ws.send(json.dumps(response_create))

            logger.info("Initial greeting triggered")

        except Exception as e:
            logger.error(f"Error sending initial greeting: {e}")

    async def handle_twilio_audio(self, audio_payload: str):
        """
        Handle audio from Twilio and send to OpenAI.

        Args:
            audio_payload: Base64 encoded mulaw audio from Twilio
        """
        try:
            from src.utils.audio_converter import base64_mulaw_to_base64_pcm16

            # Convert mulaw 8kHz to PCM16
            pcm_audio = base64_mulaw_to_base64_pcm16(audio_payload)

            if pcm_audio:
                await self.openai_client.send_audio(pcm_audio)

        except Exception as e:
            logger.error(f"Error handling Twilio audio: {e}")

    async def send_audio_to_twilio(self, audio_data: str):
        """
        Send audio from OpenAI to Twilio.

        Args:
            audio_data: Base64 encoded PCM16 audio from OpenAI
        """
        try:
            if not self.is_active:
                return

            from src.utils.audio_converter import base64_pcm16_to_base64_mulaw

            # Convert PCM16 to mulaw for Twilio
            mulaw_audio = base64_pcm16_to_base64_mulaw(audio_data)

            if mulaw_audio:
                media_message = {
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {
                        "payload": mulaw_audio
                    }
                }

                await self.twilio_ws.send(json.dumps(media_message))

        except Exception as e:
            logger.error(f"Error sending audio to Twilio: {e}")

    async def cleanup(self):
        """Clean up resources."""
        try:
            self.is_active = False
            await self.openai_client.close()
            logger.info(f"Cleaned up media stream handler for call {self.call_sid}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def handle_media_stream(websocket, path):
    """
    WebSocket handler for Twilio Media Streams.

    Args:
        websocket: WebSocket connection from Twilio
        path: WebSocket path
    """
    logger.info(f"New Media Stream connection from {websocket.remote_address}")

    handler = MediaStreamHandler(websocket)
    await handler.handle()

    logger.info("Media Stream connection closed")
