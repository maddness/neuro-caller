/**
 * VoxEngine Scenario: AI-powered Recruitment Bot
 *
 * Этот сценарий обрабатывает входящие и исходящие звонки,
 * подключая их к OpenAI Realtime API для натурального разговора
 * с потенциальными водителями такси.
 */

require(Modules.ApplicationStorage);

// Конфигурация из Application Storage
let config = {};
let openaiClient = null;
let currentCall = null;

/**
 * Инициализация конфигурации из Application Storage
 */
async function loadConfiguration() {
    try {
        // Получаем конфигурацию из Application Storage
        config.openaiApiKey = await ApplicationStorage.get('openai_api_key');
        config.taxiBrandName = await ApplicationStorage.get('taxi_brand_name') || 'Наше Такси';
        config.recruitmentPrompt = await ApplicationStorage.get('recruitment_prompt') ||
            `Вы - Анна, дружелюбный рекрутер такси-сервиса ${config.taxiBrandName}.`;

        Logger.write(`Configuration loaded. Brand: ${config.taxiBrandName}`);
        return true;
    } catch (error) {
        Logger.write(`Error loading configuration: ${error.message}`, "ERROR");
        return false;
    }
}

/**
 * Основная инструкция для AI рекрутера
 */
function getSystemInstructions() {
    return `${config.recruitmentPrompt}

Ваша задача - убедить человека стать водителем в нашем сервисе.

Важные правила:
1. Говорите кратко и естественно, как в живом разговоре
2. Представьтесь в начале разговора: "Здравствуйте! Меня зовут Анна, я из службы подбора водителей ${config.taxiBrandName}"
3. Узнайте имя собеседника и обращайтесь к нему по имени
4. Расскажите о главных преимуществах работы водителем:
   - Свободный график - работайте когда удобно вам
   - Стабильный доход - еженедельные выплаты без задержек
   - Бонусы для новых водителей - до 50,000 рублей в первый месяц
   - Круглосуточная поддержка по любым вопросам
   - Страховка и полная защита водителя
   - Приоритетные заказы в первые недели работы
5. Ответьте на все вопросы собеседника честно и подробно
6. Если человек заинтересован, предложите записать его контакты для связи с менеджером
7. Если человек отказывается, вежливо попрощайтесь и поблагодарите за время
8. Говорите ТОЛЬКО на русском языке
9. Будьте дружелюбны, энергичны и профессиональны
10. Используйте естественные интонации, паузы и эмоции в голосе
11. Если собеседник просит повторить - повторите последнюю информацию
12. Завершайте разговор фразой "Всего доброго!" или "Хорошего дня!"`;
}

/**
 * Создание и настройка OpenAI Realtime клиента
 */
async function setupOpenAIClient() {
    try {
        // Создаем клиент OpenAI Realtime API с GA версией
        openaiClient = new OpenAI.RealtimeAPIClient({
            apiKey: config.openaiApiKey,
            model: 'gpt-4o-realtime-preview-2024-10-01',
            instructions: getSystemInstructions(),
            voice: 'alloy',  // Можно использовать: alloy, echo, shimmer
            inputAudioFormat: 'pcm16',
            outputAudioFormat: 'pcm16',
            inputAudioTranscription: {
                model: 'whisper-1'
            },
            turnDetection: {
                type: 'server_vad',
                threshold: 0.5,
                prefixPaddingMs: 300,
                silenceDurationMs: 500
            },
            temperature: 0.8,
            maxResponseOutputTokens: 4096
        });

        Logger.write('OpenAI Realtime client configured successfully');
        return true;
    } catch (error) {
        Logger.write(`Error setting up OpenAI client: ${error.message}`, "ERROR");
        return false;
    }
}

/**
 * Обработка входящих звонков
 */
VoxEngine.addEventListener(AppEvents.CallAlerting, async (event) => {
    currentCall = event.call;
    Logger.write(`Incoming call from ${currentCall.callerid()}`);

    // Загружаем конфигурацию
    if (!await loadConfiguration()) {
        currentCall.hangup();
        return;
    }

    // Отвечаем на звонок
    currentCall.answer();

    // Настраиваем OpenAI клиент
    if (!await setupOpenAIClient()) {
        currentCall.say('Извините, сервис временно недоступен', Language.RU_RUSSIAN_FEMALE);
        currentCall.hangup();
        return;
    }

    // Подключаем звонок к OpenAI
    await connectCallToOpenAI();
});

/**
 * Обработка исходящих звонков (инициированных через API)
 */
VoxEngine.addEventListener(AppEvents.Started, async (event) => {
    // Проверяем, есть ли customData с номером для звонка
    const customData = VoxEngine.customData();
    if (!customData) {
        Logger.write('No custom data provided for outbound call');
        VoxEngine.terminate();
        return;
    }

    let data;
    try {
        data = JSON.parse(customData);
    } catch (error) {
        Logger.write(`Error parsing custom data: ${error.message}`, "ERROR");
        VoxEngine.terminate();
        return;
    }

    if (!data.phoneNumber) {
        Logger.write('No phone number provided in custom data');
        VoxEngine.terminate();
        return;
    }

    // Загружаем конфигурацию
    if (!await loadConfiguration()) {
        VoxEngine.terminate();
        return;
    }

    // Настраиваем OpenAI клиент
    if (!await setupOpenAIClient()) {
        VoxEngine.terminate();
        return;
    }

    // Совершаем исходящий звонок
    Logger.write(`Making outbound call to ${data.phoneNumber}`);
    currentCall = VoxEngine.callPSTN(data.phoneNumber, config.callerId || 'unknown');

    // Обработка событий звонка
    currentCall.addEventListener(CallEvents.Connected, async () => {
        Logger.write('Outbound call connected');
        await connectCallToOpenAI();
    });

    currentCall.addEventListener(CallEvents.Failed, (event) => {
        Logger.write(`Call failed: ${event.code} - ${event.reason}`, "ERROR");
        VoxEngine.terminate();
    });

    currentCall.addEventListener(CallEvents.Disconnected, () => {
        Logger.write('Call disconnected');
        VoxEngine.terminate();
    });
});

/**
 * Подключение звонка к OpenAI Realtime API
 */
async function connectCallToOpenAI() {
    try {
        // Подключаем медиа напрямую к OpenAI
        await openaiClient.connect(currentCall);

        Logger.write('Call connected to OpenAI Realtime API');

        // Отправляем начальное приветствие
        await sendInitialGreeting();

        // Обработка событий OpenAI
        openaiClient.addEventListener('conversation.item.input_audio_transcription.completed', (event) => {
            const transcript = event.transcript || '';
            Logger.write(`User said: ${transcript}`);
        });

        openaiClient.addEventListener('response.text.delta', (event) => {
            const text = event.delta || '';
            Logger.write(`AI response: ${text}`);
        });

        openaiClient.addEventListener('response.done', (event) => {
            Logger.write('AI response completed');

            // Проверяем, нужно ли завершить разговор
            const lastMessage = event.response?.output?.[0]?.content?.[0]?.text || '';
            if (shouldEndConversation(lastMessage)) {
                setTimeout(() => {
                    Logger.write('Ending conversation');
                    currentCall.hangup();
                }, 2000);
            }
        });

        openaiClient.addEventListener('error', (event) => {
            Logger.write(`OpenAI error: ${JSON.stringify(event.error)}`, "ERROR");
        });

    } catch (error) {
        Logger.write(`Error connecting to OpenAI: ${error.message}`, "ERROR");
        currentCall.say('Извините, произошла техническая ошибка', Language.RU_RUSSIAN_FEMALE);
        currentCall.hangup();
    }
}

/**
 * Отправка начального приветствия
 */
async function sendInitialGreeting() {
    try {
        // Триггерим начальное приветствие от AI
        await openaiClient.createResponse({
            modalities: ['text', 'audio'],
            instructions: 'Поприветствуйте собеседника и представьтесь. Начните с фразы "Здравствуйте!" и представьтесь как Анна из службы подбора водителей.'
        });

        Logger.write('Initial greeting triggered');
    } catch (error) {
        Logger.write(`Error sending initial greeting: ${error.message}`, "ERROR");
    }
}

/**
 * Проверка, нужно ли завершить разговор
 */
function shouldEndConversation(message) {
    const endPhrases = [
        'до свидания',
        'всего доброго',
        'всего хорошего',
        'хорошего дня',
        'удачи',
        'спасибо за звонок',
        'рада была поговорить',
        'приятно было пообщаться',
        'звоните если передумаете'
    ];

    const lowerMessage = message.toLowerCase();
    return endPhrases.some(phrase => lowerMessage.includes(phrase));
}

/**
 * Обработка завершения звонка
 */
currentCall?.addEventListener(CallEvents.Disconnected, () => {
    Logger.write('Call ended');

    // Закрываем соединение с OpenAI
    if (openaiClient) {
        openaiClient.disconnect();
    }

    // Завершаем сценарий
    VoxEngine.terminate();
});

/**
 * Обработка ошибок звонка
 */
currentCall?.addEventListener(CallEvents.Failed, (event) => {
    Logger.write(`Call failed: ${event.code} - ${event.reason}`, "ERROR");

    // Закрываем соединение с OpenAI
    if (openaiClient) {
        openaiClient.disconnect();
    }

    VoxEngine.terminate();
});

// Глобальная обработка ошибок
VoxEngine.addEventListener(AppEvents.Terminating, () => {
    Logger.write('VoxEngine scenario terminating');

    // Убеждаемся, что все соединения закрыты
    if (openaiClient) {
        openaiClient.disconnect();
    }
});