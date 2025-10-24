"""Voice webhook routes for Twilio."""
import logging
from flask import Blueprint, request, Response
from src.services.openai_service import OpenAIService
from src.services.twilio_service import TwilioService

logger = logging.getLogger(__name__)

voice_bp = Blueprint('voice', __name__, url_prefix='/voice')

# Initialize services
openai_service = OpenAIService()
twilio_service = TwilioService()


@voice_bp.route('/initial', methods=['POST'])
def initial_call():
    """Handle initial call connection."""
    try:
        call_sid = request.form.get('CallSid')
        from_number = request.form.get('From')
        to_number = request.form.get('To')

        logger.info(f"Call {call_sid} connected: {from_number} -> {to_number}")

        # Generate initial greeting
        greeting = openai_service.generate_initial_greeting(call_sid)

        # Create TwiML response
        twiml = twilio_service.create_initial_response(greeting)

        return Response(twiml, mimetype='text/xml')

    except Exception as e:
        logger.error(f"Error in initial call: {e}")
        return Response(str(e), status=500)


@voice_bp.route('/process', methods=['POST'])
def process_speech():
    """Process user speech and generate AI response."""
    try:
        call_sid = request.form.get('CallSid')
        speech_result = request.form.get('SpeechResult', '')

        logger.info(f"Call {call_sid} - User said: {speech_result}")

        if not speech_result:
            # No speech detected
            twiml = twilio_service.create_conversation_response(
                "Извините, я вас не расслышала. Можете повторить?"
            )
            return Response(twiml, mimetype='text/xml')

        # Generate AI response
        ai_response = openai_service.generate_response(speech_result, call_sid)

        logger.info(f"Call {call_sid} - AI response: {ai_response}")

        # Create TwiML response
        twiml = twilio_service.create_conversation_response(ai_response)

        return Response(twiml, mimetype='text/xml')

    except Exception as e:
        logger.error(f"Error processing speech: {e}")
        return Response(str(e), status=500)


@voice_bp.route('/status', methods=['POST'])
def call_status():
    """Handle call status updates."""
    try:
        call_sid = request.form.get('CallSid')
        call_status = request.form.get('CallStatus')

        logger.info(f"Call {call_sid} status: {call_status}")

        # Clean up conversation history when call ends
        if call_status in ['completed', 'failed', 'busy', 'no-answer']:
            openai_service.clear_history(call_sid)
            logger.info(f"Cleared conversation history for call {call_sid}")

        return Response('OK', status=200)

    except Exception as e:
        logger.error(f"Error in status callback: {e}")
        return Response(str(e), status=500)


@voice_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return {'status': 'ok', 'service': 'voice-routes'}, 200
