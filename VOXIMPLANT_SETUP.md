# 📞 Настройка Voximplant для Neuro-Caller

Подробная инструкция по миграции с Twilio на Voximplant и настройке AI-рекрутера.

## 📋 Содержание

1. [Регистрация и создание аккаунта](#регистрация)
2. [Создание приложения](#создание-приложения)
3. [Настройка сценария](#настройка-сценария)
4. [Получение и настройка номера](#настройка-номера)
5. [Настройка правил маршрутизации](#правила-маршрутизации)
6. [Конфигурация переменных](#конфигурация)
7. [Тестирование](#тестирование)
8. [Мониторинг и отладка](#мониторинг)

## 🚀 1. Регистрация и создание аккаунта {#регистрация}

### Шаг 1.1: Создание аккаунта

1. Перейдите на [voximplant.com](https://voximplant.com)
2. Нажмите **Sign Up** / **Регистрация**
3. Заполните форму регистрации:
   - Email (будет использоваться для входа)
   - Пароль
   - Название аккаунта (латиницей, например: `mycompany`)
4. Подтвердите email

### Шаг 1.2: Получение учетных данных

После регистрации в панели управления:

1. Перейдите в **Settings** → **API Keys**
2. Создайте новый API ключ
3. Сохраните:
   - **Account ID**: ваш ID аккаунта
   - **API Key**: сгенерированный ключ

## 🎯 2. Создание приложения {#создание-приложения}

### Шаг 2.1: Создание нового приложения

1. В панели управления перейдите в **Applications**
2. Нажмите **Create Application**
3. Введите:
   - **Application Name**: `recruitment_bot`
   - **Description**: `AI-powered recruitment calls`
4. Нажмите **Create**

### Шаг 2.2: Получение Application ID

После создания приложения:
1. Кликните на приложение `recruitment_bot`
2. Скопируйте **Application ID** из URL или деталей

## 📝 3. Настройка сценария {#настройка-сценария}

### Шаг 3.1: Создание сценария в Cloud IDE

1. В приложении `recruitment_bot` перейдите в **Scenarios**
2. Нажмите **Create Scenario**
3. Название: `ai_recruiter`
4. Нажмите **Create and Open in IDE**

### Шаг 3.2: Загрузка кода сценария

1. В Cloud IDE удалите весь стандартный код
2. Скопируйте содержимое файла `voximplant/recruitment_bot.js`
3. Вставьте в редактор
4. Нажмите **Save**

### Шаг 3.3: Настройка модулей

В сценарии включите необходимые модули:
1. В панели слева найдите **Modules**
2. Включите:
   - ✅ ApplicationStorage
   - ✅ OpenAI (если доступен)

## 📱 4. Получение и настройка номера {#настройка-номера}

### Вариант A: Покупка российского номера

1. Перейдите в **Phone Numbers** → **Buy Phone Number**
2. Выберите страну: **Russia**
3. Выберите город (например, Москва +7495 или +7499)
4. Выберите номер из списка
5. Нажмите **Buy**

### Вариант B: Использование тестового номера

Для тестирования можно использовать тестовые номера Voximplant:
1. В **Phone Numbers** → **Test Numbers**
2. Получите тестовый номер для исходящих звонков

### Шаг 4.1: Привязка номера к приложению

1. В **Phone Numbers** выберите купленный номер
2. В поле **Application** выберите `recruitment_bot`
3. Сохраните изменения

## 🔄 5. Правила маршрутизации {#правила-маршрутизации}

### Шаг 5.1: Создание правила для исходящих звонков

1. В приложении `recruitment_bot` перейдите в **Rules**
2. Нажмите **Create Rule**
3. Настройте:
   - **Rule Name**: `outbound_calls`
   - **Pattern**: `.*` (все номера)
   - **Scenario**: `ai_recruiter`
4. Сохраните правило

### Шаг 5.2: Получение Rule ID

После создания правила скопируйте его **Rule ID** для использования в конфигурации.

## ⚙️ 6. Конфигурация переменных {#конфигурация}

### Шаг 6.1: Настройка Application Storage

В панели управления Voximplant:

1. Перейдите в приложение `recruitment_bot`
2. Откройте **Application Storage**
3. Добавьте переменные:

```
openai_api_key = sk-xxxxxxxxxxxxxxxx
taxi_brand_name = Ваше Такси
recruitment_prompt = Кастомный промпт для рекрутера (опционально)
```

### Шаг 6.2: Создание файла .env.voximplant

Скопируйте `.env.voximplant.example` в `.env.voximplant`:

```bash
cp .env.voximplant.example .env.voximplant
```

Заполните переменные:

```env
# Voximplant Configuration
VOXIMPLANT_ACCOUNT_ID=12345              # из Settings → Account
VOXIMPLANT_API_KEY=abc123def456          # из Settings → API Keys
VOXIMPLANT_APP_ID=67890                  # из Applications → recruitment_bot
VOXIMPLANT_RULE_ID=11111                 # из Rules → outbound_calls
VOXIMPLANT_USERNAME=user@recruitment_bot.mycompany.voximplant.com
VOXIMPLANT_PASSWORD=your_password
VOXIMPLANT_PHONE_NUMBER=+74951234567     # ваш купленный номер

# OpenAI Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# Taxi Brand Configuration
TAXI_BRAND_NAME=Ваше Такси
```

### Шаг 6.3: Формирование Username

Username формируется по шаблону:
```
user@app_name.account_name.voximplant.com
```

Где:
- `user` - любое имя пользователя
- `app_name` - название вашего приложения (recruitment_bot)
- `account_name` - название вашего аккаунта

## 🧪 7. Тестирование {#тестирование}

### Шаг 7.1: Установка зависимостей

```bash
pip install -r requirements_voximplant.txt
```

### Шаг 7.2: Настройка OpenAI в Application Storage

```bash
cd voximplant
python vox_manager.py
```

Скрипт автоматически настроит OpenAI параметры в Application Storage.

### Шаг 7.3: Тестовый звонок

```bash
# Проверка подключения
python make_call_vox.py +79991234567 --test

# Реальный звонок
python make_call_vox.py +79991234567

# Звонок с настройкой OpenAI
python make_call_vox.py +79991234567 --configure

# Звонок со статистикой
python make_call_vox.py +79991234567 --stats
```

## 📊 8. Мониторинг и отладка {#мониторинг}

### Просмотр логов

1. В панели Voximplant перейдите в **Logs**
2. Фильтры:
   - **Application**: recruitment_bot
   - **Scenario**: ai_recruiter
   - **Time Range**: последние 24 часа

### Отладка сценария

1. В Cloud IDE используйте `Logger.write()` для отладки
2. Все логи будут видны в разделе **Logs**

### Проверка биллинга

1. **Billing** → **Current Balance** - текущий баланс
2. **Billing** → **Call History** - история звонков с тарификацией

## 🔧 Troubleshooting

### Ошибка: "Failed to authenticate"

- Проверьте правильность `VOXIMPLANT_API_KEY` и `VOXIMPLANT_ACCOUNT_ID`
- Убедитесь, что API ключ активен в панели управления

### Ошибка: "Failed to start call"

- Проверьте баланс аккаунта
- Убедитесь, что номер привязан к приложению
- Проверьте правильность `VOXIMPLANT_RULE_ID`

### Ошибка: "OpenAI connection failed"

- Проверьте `openai_api_key` в Application Storage
- Убедитесь, что у OpenAI есть доступ к Realtime API
- Проверьте баланс OpenAI

### Нет звука при звонке

- Проверьте логи на наличие ошибок OpenAI
- Убедитесь, что сценарий использует правильную версию OpenAI клиента
- Проверьте настройки аудио форматов в сценарии

## 💰 Примерная стоимость

### Voximplant
- **Российские звонки**: $0.01-0.03/мин
- **Номер телефона**: ~$2-5/месяц
- **Минимальное пополнение**: $10

### OpenAI Realtime API
- **Входящее аудио**: $0.06/мин
- **Исходящее аудио**: $0.24/мин

### Итого за звонок (5 минут)
- Voximplant: ~$0.10
- OpenAI: ~$0.66
- **Всего**: ~$0.76 (экономия 12% по сравнению с Twilio)

## 📚 Полезные ссылки

- [Voximplant Documentation](https://voximplant.com/docs)
- [Voximplant API Reference](https://voximplant.com/docs/references/httpapi)
- [VoxEngine Reference](https://voximplant.com/docs/references/voxengine)
- [OpenAI Realtime API on Voximplant](https://voximplant.com/docs/guides/voice-ai/openai)

## ✅ Checklist перед запуском

- [ ] Создан аккаунт Voximplant
- [ ] Создано приложение `recruitment_bot`
- [ ] Загружен сценарий `ai_recruiter`
- [ ] Куплен или получен тестовый номер
- [ ] Создано правило маршрутизации
- [ ] Настроены переменные в Application Storage
- [ ] Заполнен файл `.env.voximplant`
- [ ] Пополнен баланс аккаунта
- [ ] Протестирован звонок

---

После выполнения всех шагов система готова к работе! 🎉