/**
 * VoxEngine Scenario: AI-powered Recruitment Bot (Simplified)
 * Простая версия для тестирования базового функционала
 */

require(Modules.ApplicationStorage);

let config = {};
let currentCall = null;

/**
 * Инициализация конфигурации из Application Storage
 */
async function loadConfiguration() {
    try {
        config.openaiApiKey = await ApplicationStorage.get('openai_api_key');
        config.taxiBrandName = await ApplicationStorage.get('taxi_brand_name') || 'Наше Такси';

        Logger.write(`Configuration loaded. Brand: ${config.taxiBrandName}`);
        Logger.write(`OpenAI key present: ${config.openaiApiKey ? 'Yes' : 'No'}`);
        return true;
    } catch (error) {
        Logger.write(`Error loading configuration: ${error.message}`);
        return false;
    }
}

/**
 * Обработка исходящих звонков
 */
VoxEngine.addEventListener(AppEvents.Started, async (event) => {
    Logger.write('=== Scenario Started ===');

    // Получаем customData
    const customData = VoxEngine.customData();
    if (!customData) {
        Logger.write('No custom data provided');
        VoxEngine.terminate();
        return;
    }

    let data;
    try {
        data = JSON.parse(customData);
        Logger.write(`Parsed data: phoneNumber = ${data.phoneNumber}`);
    } catch (error) {
        Logger.write(`Error parsing custom data: ${error.message}`);
        VoxEngine.terminate();
        return;
    }

    if (!data.phoneNumber) {
        Logger.write('No phone number in custom data');
        VoxEngine.terminate();
        return;
    }

    // Загружаем конфигурацию
    Logger.write('Loading configuration...');
    if (!await loadConfiguration()) {
        VoxEngine.terminate();
        return;
    }

    // Совершаем исходящий звонок
    Logger.write(`Making outbound call to ${data.phoneNumber}`);

    try {
        currentCall = VoxEngine.callPSTN(data.phoneNumber, '74999384362');

        currentCall.addEventListener(CallEvents.Connected, async () => {
            Logger.write('=== Call Connected ===');

            // Простое голосовое приветствие
            currentCall.say(
                `Здравствуйте! Меня зовут Анна, я из службы подбора водителей ${config.taxiBrandName}. ` +
                'Мы ищем водителей для работы в нашем сервисе. ' +
                'Предлагаем гибкий график и еженедельные выплаты. ',
                Language.RU_RUSSIAN_FEMALE
            );

            // Простой сбор речи
            currentCall.startPlayback('https://cdn.voximplant.com/static/silence.mp3', true);

            // Ждем 30 секунд и завершаем
            setTimeout(() => {
                Logger.write('Ending call after 30 seconds');
                currentCall.hangup();
            }, 30000);
        });

        currentCall.addEventListener(CallEvents.Failed, (event) => {
            Logger.write(`Call failed: ${event.code} - ${event.reason}`);
            VoxEngine.terminate();
        });

        currentCall.addEventListener(CallEvents.Disconnected, () => {
            Logger.write('=== Call Disconnected ===');
            VoxEngine.terminate();
        });

    } catch (error) {
        Logger.write(`Error making call: ${error.message}`);
        VoxEngine.terminate();
    }
});

// Глобальная обработка завершения
VoxEngine.addEventListener(AppEvents.Terminating, () => {
    Logger.write('=== VoxEngine Terminating ===');
});