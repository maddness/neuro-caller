"""Voice webhook routes for Twilio with Realtime API support."""
import logging
from flask import Blueprint, request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from src.config import config

logger = logging.getLogger(__name__)

voice_bp = Blueprint('voice', __name__, url_prefix='/voice')


@voice_bp.route('/initial', methods=['POST'])
def initial_call():
    """Handle initial call connection with Media Streams."""
    try:
        call_sid = request.form.get('CallSid')
        from_number = request.form.get('From')
        to_number = request.form.get('To')

        logger.info(f"Call {call_sid} connected: {from_number} -> {to_number}")

        # Create TwiML response with Stream
        response = VoiceResponse()

        # Optional: Add a brief intro before connecting to stream
        # response.say("Соединяем вас с нашим рекрутером...", voice='Polly.Tatyana', language='ru-RU')

        # Connect to Media Stream (WebSocket)
        connect = Connect()
        websocket_port = config.PORT + 1
        stream_url = config.BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')
        stream_url = f"{stream_url}:{websocket_port}/media-stream"

        stream = Stream(url=stream_url)
        connect.append(stream)
        response.append(connect)

        logger.info(f"Connecting call {call_sid} to Media Stream: {stream_url}")

        return Response(str(response), mimetype='text/xml')

    except Exception as e:
        logger.error(f"Error in initial call: {e}")
        return Response(str(e), status=500)


@voice_bp.route('/status', methods=['POST'])
def call_status():
    """Handle call status updates."""
    try:
        call_sid = request.form.get('CallSid')
        call_status = request.form.get('CallStatus')

        logger.info(f"Call {call_sid} status: {call_status}")

        return Response('OK', status=200)

    except Exception as e:
        logger.error(f"Error in status callback: {e}")
        return Response(str(e), status=500)


@voice_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return {'status': 'ok', 'service': 'voice-routes'}, 200
