"""OpenAI service for text-to-speech and conversation."""
import logging
from typing import Optional
from openai import OpenAI
from src.config import config

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI API."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.conversation_history = []

    def generate_response(self, user_message: str, call_sid: str) -> str:
        """
        Generate AI response based on user message.

        Args:
            user_message: The transcribed user message
            call_sid: Unique call identifier

        Returns:
            AI-generated response text
        """
        try:
            # Initialize conversation history for new calls
            if not hasattr(self, f'history_{call_sid}'):
                system_prompt = config.RECRUITMENT_PROMPT.format(
                    brand=config.TAXI_BRAND_NAME
                )
                setattr(self, f'history_{call_sid}', [
                    {"role": "system", "content": system_prompt + """

Важные правила:
1. Говорите кратко и естественно, как в живом разговоре
2. Представьтесь в начале разговора
3. Узнайте имя собеседника
4. Расскажите о преимуществах работы водителем:
   - Гибкий график
   - Еженедельные выплаты
   - Бонусы и премии
   - Поддержка 24/7
5. Ответьте на вопросы собеседника
6. Если человек заинтересован, предложите оставить контакты для менеджера
7. Если человек отказывается, вежливо попрощайтесь
8. Отвечайте на русском языке
9. Будьте дружелюбны и профессиональны
"""}
                ])

            history = getattr(self, f'history_{call_sid}')
            history.append({"role": "user", "content": user_message})

            # Generate response
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=history,
                max_tokens=150,
                temperature=0.7
            )

            assistant_message = response.choices[0].message.content
            history.append({"role": "assistant", "content": assistant_message})

            logger.info(f"Generated response for call {call_sid}: {assistant_message}")
            return assistant_message

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Извините, у меня возникли технические проблемы. Могу я перезвонить вам позже?"

    def generate_initial_greeting(self, call_sid: str) -> str:
        """
        Generate initial greeting for the call.

        Args:
            call_sid: Unique call identifier

        Returns:
            Initial greeting text
        """
        greeting = f"Здравствуйте! Меня зовут Анна, я звоню из {config.TAXI_BRAND_NAME}. " \
                   f"У вас есть минутка? Я хотела бы рассказать о возможности работы водителем в нашем сервисе."

        # Initialize conversation history
        if not hasattr(self, f'history_{call_sid}'):
            system_prompt = config.RECRUITMENT_PROMPT.format(brand=config.TAXI_BRAND_NAME)
            setattr(self, f'history_{call_sid}', [
                {"role": "system", "content": system_prompt}
            ])

        history = getattr(self, f'history_{call_sid}')
        history.append({"role": "assistant", "content": greeting})

        return greeting

    def clear_history(self, call_sid: str):
        """Clear conversation history for a call."""
        if hasattr(self, f'history_{call_sid}'):
            delattr(self, f'history_{call_sid}')
