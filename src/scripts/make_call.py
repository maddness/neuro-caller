"""Script to initiate outbound calls."""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import config
from src.services.twilio_service import TwilioService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def make_call(phone_number: str):
    """
    Initiate a call to the specified phone number.

    Args:
        phone_number: Phone number to call (format: +79991234567)
    """
    try:
        # Validate configuration
        config.validate()

        # Initialize Twilio service
        twilio_service = TwilioService()

        # Make the call
        logger.info(f"Initiating call to {phone_number}...")
        call_sid = twilio_service.make_call(phone_number)

        if call_sid:
            logger.info(f"Call initiated successfully!")
            logger.info(f"Call SID: {call_sid}")
            logger.info(f"Monitor the call at: https://console.twilio.com")
        else:
            logger.error("Failed to initiate call")
            sys.exit(1)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error making call: {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python src/scripts/make_call.py <phone_number>")
        print("Example: python src/scripts/make_call.py +79991234567")
        sys.exit(1)

    phone_number = sys.argv[1]

    # Validate phone number format
    if not phone_number.startswith('+'):
        logger.error("Phone number must start with '+' (e.g., +79991234567)")
        sys.exit(1)

    make_call(phone_number)
