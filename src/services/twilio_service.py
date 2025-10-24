"""Twilio service for phone call management."""
import logging
from typing import Optional
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from src.config import config

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for managing Twilio phone calls."""

    def __init__(self):
        """Initialize Twilio client."""
        self.client = Client(
            config.TWILIO_ACCOUNT_SID,
            config.TWILIO_AUTH_TOKEN
        )

    def make_call(self, to_number: str) -> Optional[str]:
        """
        Initiate an outbound call.

        Args:
            to_number: Phone number to call (format: +79991234567)

        Returns:
            Call SID if successful, None otherwise
        """
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=config.TWILIO_PHONE_NUMBER,
                url=f"{config.BASE_URL}/voice/initial",
                status_callback=f"{config.BASE_URL}/voice/status",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
            )
            logger.info(f"Call initiated to {to_number}, SID: {call.sid}")
            return call.sid
        except Exception as e:
            logger.error(f"Error making call to {to_number}: {e}")
            return None

    def create_initial_response(self, greeting_text: str) -> str:
        """
        Create initial TwiML response with greeting.

        Args:
            greeting_text: Initial greeting message

        Returns:
            TwiML XML string
        """
        response = VoiceResponse()

        # Say greeting with Russian voice
        response.say(
            greeting_text,
            voice='Polly.Tatyana',  # Russian female voice
            language='ru-RU'
        )

        # Gather user input
        gather = Gather(
            input='speech',
            action='/voice/process',
            language='ru-RU',
            speech_timeout='auto',
            timeout=5
        )
        response.append(gather)

        # If no input, say goodbye
        response.say(
            "Извините, я вас не слышу. До свидания!",
            voice='Polly.Tatyana',
            language='ru-RU'
        )
        response.hangup()

        return str(response)

    def create_conversation_response(self, ai_response: str) -> str:
        """
        Create TwiML response for ongoing conversation.

        Args:
            ai_response: AI-generated response text

        Returns:
            TwiML XML string
        """
        response = VoiceResponse()

        # Say AI response
        response.say(
            ai_response,
            voice='Polly.Tatyana',
            language='ru-RU'
        )

        # Check if conversation should end
        end_phrases = ['до свидания', 'всего доброго', 'прощайте', 'спасибо, не интересно']
        should_end = any(phrase in ai_response.lower() for phrase in end_phrases)

        if should_end:
            response.hangup()
        else:
            # Continue gathering input
            gather = Gather(
                input='speech',
                action='/voice/process',
                language='ru-RU',
                speech_timeout='auto',
                timeout=5
            )
            response.append(gather)

            # Timeout message
            response.say(
                "Вы ещё здесь? Если у вас есть вопросы, я слушаю.",
                voice='Polly.Tatyana',
                language='ru-RU'
            )
            response.hangup()

        return str(response)

    def get_call_status(self, call_sid: str) -> Optional[dict]:
        """
        Get call status information.

        Args:
            call_sid: Unique call identifier

        Returns:
            Call information dictionary
        """
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'sid': call.sid,
                'status': call.status,
                'duration': call.duration,
                'from': call.from_,
                'to': call.to
            }
        except Exception as e:
            logger.error(f"Error fetching call status: {e}")
            return None
