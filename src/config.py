"""Configuration settings for the neuro-caller application."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Server
    PORT = int(os.getenv('PORT', 3000))
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:3000')

    # Taxi Brand
    TAXI_BRAND_NAME = os.getenv('TAXI_BRAND_NAME', 'Наше Такси')
    RECRUITMENT_PROMPT = os.getenv(
        'RECRUITMENT_PROMPT',
        'Вы - дружелюбный рекрутер такси-сервиса {brand}. '
        'Ваша задача - убедить человека стать водителем в нашем сервисе.'
    )

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        required = [
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_PHONE_NUMBER',
            'OPENAI_API_KEY'
        ]
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


config = Config()
